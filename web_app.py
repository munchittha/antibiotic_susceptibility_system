"""Web application for the Antibiotic Susceptibility Reporting System."""

from collections import defaultdict
from datetime import datetime
import os

from flask import Flask, flash, redirect, render_template, request, session, url_for
from pony.orm import ObjectNotFound, db_session, flush

from .database import init_database
from .models import Organism, Patient, Reporter, Specimen, Susceptibility, Visit
from .utils.ast_options import (
    ORGANISMS_BY_GRAM_GROUP,
    filter_organisms_by_names,
    get_all_organism_names,
    get_antibiotics_for_organism,
    get_likely_organisms_for_specimen,
    get_mic_options_for_antibiotic,
    get_mic_options_for_antibiotics,
)
from .utils.validation import SPECIMEN_TYPES, WARD_NAMES


VALID_RESULTS = {"S", "I", "R"}
SYSTEM_PIN = os.environ.get("SYSTEM_PIN", "1234")


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "beginner-friendly-development-key",
    )
    init_database()
    register_routes(app)
    return app


def parse_date(value: str):
    """Convert a YYYY-MM-DD string to a date object."""
    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_datetime(value: str):
    """Convert an HTML datetime-local value to a datetime object."""
    return datetime.strptime(value, "%Y-%m-%dT%H:%M")


def parse_birth_date_from_parts(day: str, month: str, year: str):
    """Convert separate day, month, and year fields to a date object."""
    day = day.strip().zfill(2)
    month = month.strip().zfill(2)
    year = year.strip()
    return parse_date(f"{year}-{month}-{day}")


def clean_upper(value: str) -> str:
    """Trim user input and convert it to uppercase for validation."""
    return value.strip().upper()


def get_entity_or_none(entity_class, entity_id):
    """Safely find an entity by primary key."""
    try:
        return entity_class[int(entity_id)]
    except (TypeError, ValueError, ObjectNotFound):
        return None


def clear_current_workflow() -> None:
    """Remove temporary IDs saved while entering one AST workflow."""
    for key in (
        "current_patient_hn",
        "current_visit_id",
        "current_specimen_id",
        "current_organism_id",
    ):
        session.pop(key, None)


def register_routes(app: Flask) -> None:
    """Register all website pages and form handlers."""

    @app.before_request
    def require_pin():
        """Send users to the PIN page before they can use the system."""
        allowed_endpoints = {"login", "static"}
        if request.endpoint in allowed_endpoints:
            return None

        if not session.get("pin_verified"):
            return redirect(url_for("login"))

        return None

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            staff_id = clean_upper(request.form.get("staff_id", ""))
            pin = request.form.get("pin", "").strip()

            if not staff_id:
                flash("Staff ID is required.", "error")
                return render_template("login.html")

            if pin == SYSTEM_PIN:
                session["pin_verified"] = True
                session["staff_id"] = staff_id
                flash("Login successful.", "success")
                return redirect(url_for("add_patient"))

            flash("Incorrect PIN. Please try again.", "error")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have logged out.", "success")
        return redirect(url_for("login"))

    @app.route("/")
    @db_session
    def dashboard():
        stats = {
            "patients": Patient.select().count(),
            "visits": Visit.select().count(),
            "specimens": Specimen.select().count(),
            "organisms": Organism.select().count(),
            "results": Susceptibility.select().count(),
        }
        recent_results = sorted(
            Susceptibility.select()[:],
            key=lambda result: result.report_date,
            reverse=True,
        )[:8]
        return render_template("dashboard.html", stats=stats, recent_results=recent_results)

    @app.route("/reporters/new")
    def add_reporter():
        flash("Reporter details are now entered during login and AST reporting.", "error")
        return redirect(url_for("dashboard"))

    @app.route("/patients/new", methods=["GET", "POST"])
    @db_session
    def add_patient():
        if request.method == "POST":
            hn = clean_upper(request.form.get("hn", ""))
            first_name = request.form.get("first_name", "").strip()
            last_name = request.form.get("last_name", "").strip()
            gender = request.form.get("gender", "").strip()

            try:
                date_of_birth = parse_birth_date_from_parts(
                    request.form.get("birth_day", ""),
                    request.form.get("birth_month", ""),
                    request.form.get("birth_year", ""),
                )
            except ValueError:
                flash("Date of birth must be a valid date.", "error")
                return render_template("patient_form.html")

            if not all([hn, first_name, last_name, gender]):
                flash("All patient fields are required.", "error")
            elif gender not in {"Male", "Female"}:
                flash("Please choose Male or Female.", "error")
            else:
                patient = Patient.get(hn=hn)
                if patient:
                    patient.first_name = first_name
                    patient.last_name = last_name
                    patient.date_of_birth = date_of_birth
                    patient.gender = gender
                    flash("Existing patient found. Continue with a new visit.", "success")
                else:
                    patient = Patient(
                        hn=hn,
                        first_name=first_name,
                        last_name=last_name,
                        date_of_birth=date_of_birth,
                        gender=gender,
                    )
                    flush()
                    flash(
                        "Patient added successfully. Continue with visit details.",
                        "success",
                    )

                session["current_patient_hn"] = patient.hn
                return redirect(url_for("add_visit"))

        return render_template("patient_form.html")

    @app.route("/visits/new", methods=["GET", "POST"])
    @db_session
    def add_visit():
        if request.method == "POST":
            hn = clean_upper(
                request.form.get("hn", "") or session.get("current_patient_hn", "")
            )
            patient = Patient.get(hn=hn)
            ward = request.form.get("ward", "").strip()

            try:
                visit_date = parse_date(request.form.get("visit_date", ""))
            except ValueError:
                flash("Visit date must be a valid date.", "error")
                return render_template(
                    "visit_form.html",
                    patient_hn=session.get("current_patient_hn"),
                    ward_names=WARD_NAMES,
                )

            if not patient:
                flash("Patient HN was not found.", "error")
            elif not ward:
                flash("Ward is required.", "error")
            elif ward not in WARD_NAMES:
                flash("Please choose a ward from the list.", "error")
            else:
                visit = Visit(visit_date=visit_date, ward=ward, patient=patient)
                flush()
                session["current_visit_id"] = visit.visit_id
                flash("Visit added successfully. Continue with specimen details.", "success")
                return redirect(url_for("add_specimen"))

        return render_template(
            "visit_form.html",
            patient_hn=session.get("current_patient_hn"),
            ward_names=WARD_NAMES,
        )

    @app.route("/specimens/new", methods=["GET", "POST"])
    @db_session
    def add_specimen():
        visit_id = session.get("current_visit_id")
        visit = get_entity_or_none(Visit, visit_id)

        if not visit:
            flash("Please add a visit before adding a specimen.", "error")
            return redirect(url_for("add_visit"))

        if request.method == "POST":
            specimen_type = request.form.get("specimen_type", "").strip()

            try:
                collection_date_time = parse_datetime(
                    request.form.get("collection_date_time", "")
                )
            except ValueError:
                flash("Collection date and time must be valid.", "error")
                return render_template(
                    "specimen_form.html", specimen_types=SPECIMEN_TYPES
                )

            if specimen_type not in SPECIMEN_TYPES:
                flash("Please choose a valid specimen type.", "error")
            else:
                specimen = Specimen(
                    specimen_type=specimen_type,
                    collection_date_time=collection_date_time,
                    visit=visit,
                )
                flush()
                session["current_specimen_id"] = specimen.specimen_id
                flash("Specimen added successfully. Continue with organism details.", "success")
                return redirect(url_for("add_organism"))

        return render_template(
            "specimen_form.html", specimen_types=SPECIMEN_TYPES
        )

    @app.route("/organisms/new", methods=["GET", "POST"])
    @db_session
    def add_organism():
        specimen_id = session.get("current_specimen_id")
        specimen = get_entity_or_none(Specimen, specimen_id)

        if not specimen:
            flash("Please add a specimen before adding an organism.", "error")
            return redirect(url_for("add_specimen"))

        if request.method == "POST":
            organism_name = request.form.get("organism_name", "").strip()

            if not organism_name:
                flash("Organism name is required.", "error")
            elif organism_name not in get_all_organism_names():
                flash("Please choose an organism from the list.", "error")
            else:
                organism = Organism(organism_name=organism_name, specimen=specimen)
                flush()
                session["current_organism_id"] = organism.organism_id
                flash("Organism added successfully. Continue with AST result.", "success")
                return redirect(url_for("add_susceptibility"))

        likely_organisms = get_likely_organisms_for_specimen(specimen.specimen_type)
        likely_organisms_by_group = filter_organisms_by_names(likely_organisms)

        return render_template(
            "organism_form.html",
            all_organisms_by_group=ORGANISMS_BY_GRAM_GROUP,
            likely_organisms_by_group=likely_organisms_by_group,
            specimen_type=specimen.specimen_type,
        )

    @app.route("/susceptibilities/new", methods=["GET", "POST"])
    @db_session
    def add_susceptibility():
        organism_id = session.get("current_organism_id")
        organism = get_entity_or_none(Organism, organism_id)

        if not organism:
            flash("Please add an organism before recording an AST result.", "error")
            return redirect(url_for("add_organism"))

        antibiotic_options = get_antibiotics_for_organism(organism.organism_name)
        mic_options_by_antibiotic = get_mic_options_for_antibiotics(antibiotic_options)

        if request.method == "POST":
            staff_id = session.get("staff_id", "")
            reporter_name = request.form.get("reporter_name", "").strip()
            antibiotic_name = request.form.get("antibiotic_name", "").strip()
            result = clean_upper(request.form.get("result", ""))
            mic_value = request.form.get("mic_value", "").strip() or None
            next_action = request.form.get("next_action", "finish")
            reporter = Reporter.get(staff_id=staff_id)

            try:
                report_date = parse_date(request.form.get("report_date", ""))
            except ValueError:
                flash("Report date must be a valid date.", "error")
                return render_template(
                    "susceptibility_form.html",
                    antibiotic_options=antibiotic_options,
                    mic_options_by_antibiotic=mic_options_by_antibiotic,
                    current_organism=organism,
                )

            if not staff_id:
                flash("Please log in with Staff ID again.", "error")
            elif not reporter_name:
                flash("Reporter name is required.", "error")
            elif not antibiotic_name:
                flash("Antibiotic name is required.", "error")
            elif antibiotic_options and antibiotic_name not in antibiotic_options:
                flash("Please choose an antibiotic from the list.", "error")
            elif result not in VALID_RESULTS:
                flash('Result must be "S", "I", or "R".', "error")
            elif mic_value not in get_mic_options_for_antibiotic(antibiotic_name).get(
                result, []
            ):
                flash("Please choose a MIC value that matches the selected result.", "error")
            else:
                if reporter:
                    reporter.name = reporter_name
                else:
                    reporter = Reporter(staff_id=staff_id, name=reporter_name)

                Susceptibility(
                    antibiotic_name=antibiotic_name,
                    result=result,
                    mic_value=mic_value,
                    report_date=report_date,
                    organism=organism,
                    reporter=reporter,
                )
                session["last_reporter_name"] = reporter_name
                session["last_report_date"] = report_date.isoformat()

                if next_action == "add_another":
                    flash(
                        "Result saved. Add another antibiotic for the same organism.",
                        "success",
                    )
                    return redirect(url_for("add_susceptibility"))

                clear_current_workflow()
                flash("Susceptibility result recorded successfully.", "success")
                return redirect(url_for("dashboard"))

        return render_template(
            "susceptibility_form.html",
            antibiotic_options=antibiotic_options,
            mic_options_by_antibiotic=mic_options_by_antibiotic,
            current_organism=organism,
            last_reporter_name=session.get("last_reporter_name", ""),
            last_report_date=session.get("last_report_date", ""),
        )

    @app.route("/susceptibilities/<int:sus_id>/edit", methods=["GET", "POST"])
    @db_session
    def edit_susceptibility(sus_id):
        susceptibility = get_entity_or_none(Susceptibility, sus_id)
        if not susceptibility:
            flash("Susceptibility result not found.", "error")
            return redirect(url_for("dashboard"))

        antibiotic_options = get_antibiotics_for_organism(
            susceptibility.organism.organism_name
        )
        mic_options_by_antibiotic = get_mic_options_for_antibiotics(antibiotic_options)

        if request.method == "POST":
            reporter_name = request.form.get("reporter_name", "").strip()
            antibiotic_name = request.form.get("antibiotic_name", "").strip()
            result = clean_upper(request.form.get("result", ""))
            mic_value = request.form.get("mic_value", "").strip() or None

            try:
                report_date = parse_date(request.form.get("report_date", ""))
            except ValueError:
                flash("Report date must be a valid date.", "error")
                return render_template(
                    "susceptibility_form.html",
                    antibiotic_options=antibiotic_options,
                    mic_options_by_antibiotic=mic_options_by_antibiotic,
                    current_organism=susceptibility.organism,
                    susceptibility=susceptibility,
                    edit_mode=True,
                )

            if not reporter_name:
                flash("Reporter name is required.", "error")
            elif not antibiotic_name:
                flash("Antibiotic name is required.", "error")
            elif antibiotic_options and antibiotic_name not in antibiotic_options:
                flash("Please choose an antibiotic from the list.", "error")
            elif result not in VALID_RESULTS:
                flash('Result must be "S", "I", or "R".', "error")
            elif mic_value not in get_mic_options_for_antibiotic(antibiotic_name).get(
                result, []
            ):
                flash("Please choose a MIC value that matches the selected result.", "error")
            else:
                susceptibility.reporter.name = reporter_name
                susceptibility.antibiotic_name = antibiotic_name
                susceptibility.result = result
                susceptibility.mic_value = mic_value
                susceptibility.report_date = report_date
                flash("Susceptibility result updated successfully.", "success")
                return redirect(url_for("dashboard"))

        return render_template(
            "susceptibility_form.html",
            antibiotic_options=antibiotic_options,
            mic_options_by_antibiotic=mic_options_by_antibiotic,
            current_organism=susceptibility.organism,
            susceptibility=susceptibility,
            edit_mode=True,
        )

    @app.route("/search")
    @db_session
    def search():
        hn = clean_upper(request.args.get("hn", ""))
        name = request.args.get("name", "").strip().lower()
        patients = []

        if hn:
            patient = Patient.get(hn=hn)
            patients = [patient] if patient else []
        elif name:
            patients = [
                patient
                for patient in Patient.select()[:]
                if name in patient.first_name.lower() or name in patient.last_name.lower()
            ]

        return render_template("search.html", patients=patients, hn=hn, name=name)

    @app.route("/patients/<int:patient_id>")
    @db_session
    def patient_history(patient_id):
        patient = get_entity_or_none(Patient, patient_id)
        if not patient:
            flash("Patient not found.", "error")
            return redirect(url_for("search"))

        visits = sorted(patient.visits, key=lambda visit: visit.visit_date)
        return render_template("patient_history.html", patient=patient, visits=visits)

    @app.route("/reports/resistance")
    @db_session
    def resistance_report():
        selected_organism = request.args.get("organism", "").strip()
        susceptibilities = Susceptibility.select()[:]
        organisms = sorted({s.organism.organism_name for s in susceptibilities})

        antibiotic_counts = defaultdict(lambda: {"S": 0, "I": 0, "R": 0})
        organism_counts = defaultdict(lambda: {"total": 0, "resistant": 0})
        top_antibiotics = []

        for susceptibility in susceptibilities:
            antibiotic_counts[susceptibility.antibiotic_name][susceptibility.result] += 1
            organism_name = susceptibility.organism.organism_name
            organism_counts[organism_name]["total"] += 1
            if susceptibility.result == "R":
                organism_counts[organism_name]["resistant"] += 1

        organism_percentages = {
            name: (values["resistant"] / values["total"]) * 100
            for name, values in organism_counts.items()
            if values["total"]
        }
        organism_chart = sorted(
            (
                {
                    "name": name,
                    "percentage": percentage,
                    "resistant": organism_counts[name]["resistant"],
                    "total": organism_counts[name]["total"],
                }
                for name, percentage in organism_percentages.items()
            ),
            key=lambda item: item["percentage"],
            reverse=True,
        )

        if selected_organism:
            totals = defaultdict(lambda: {"total": 0, "resistant": 0})
            for susceptibility in susceptibilities:
                if susceptibility.organism.organism_name.lower() == selected_organism.lower():
                    totals[susceptibility.antibiotic_name]["total"] += 1
                    if susceptibility.result == "R":
                        totals[susceptibility.antibiotic_name]["resistant"] += 1

            for antibiotic, values in totals.items():
                percentage = (values["resistant"] / values["total"]) * 100
                top_antibiotics.append(
                    {
                        "name": antibiotic,
                        "percentage": percentage,
                        "resistant": values["resistant"],
                        "total": values["total"],
                    }
                )
            top_antibiotics.sort(key=lambda item: item["percentage"], reverse=True)

        return render_template(
            "resistance_report.html",
            antibiotic_counts=dict(antibiotic_counts),
            organism_chart=organism_chart,
            organism_percentages=organism_percentages,
            organisms=organisms,
            selected_organism=selected_organism,
            top_antibiotics=top_antibiotics,
        )

app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)

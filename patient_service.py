from datetime import datetime

from pony.orm import ObjectNotFound, db_session, select

from models import Organism, Patient, Reporter, Specimen, Susceptibility, Visit


VALID_RESULTS = {"S", "I", "R"}


def read_date(prompt):
    while True:
        value = input(prompt).strip()
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            print("Please enter the date in YYYY-MM-DD format.")


def read_datetime(prompt):
    while True:
        value = input(prompt).strip()
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M")
        except ValueError:
            print("Please enter date and time in YYYY-MM-DD HH:MM format.")


def read_required(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("This field is required.")


def read_result(prompt):
    while True:
        value = input(prompt).strip().upper()
        if value in VALID_RESULTS:
            return value
        print('Result must be "S", "I", or "R".')


def print_patient_summary(patient):
    print(f"\nPatient ID: {patient.patient_id}")
    print(f"HN: {patient.hn}")
    print(f"Name: {patient.first_name} {patient.last_name}")
    print(f"Date of Birth: {patient.date_of_birth}")
    print(f"Gender: {patient.gender}")


@db_session
def add_reporter():
    print("\n--- Add Reporter ---")
    staff_id = read_required("Staff ID: ").upper()

    if Reporter.get(staff_id=staff_id):
        print("A reporter with this Staff ID already exists.")
        return

    name = read_required("Name: ")
    reporter = Reporter(staff_id=staff_id, name=name)
    print(f"Reporter added successfully. Reporter ID: {reporter.user_id}")


@db_session
def add_patient():
    print("\n--- Add Patient ---")
    hn = read_required("HN: ").upper()

    if Patient.get(hn=hn):
        print("A patient with this HN already exists.")
        return

    first_name = read_required("First name: ")
    last_name = read_required("Last name: ")
    date_of_birth = read_date("Date of birth (YYYY-MM-DD): ")
    gender = read_required("Gender: ").upper()

    patient = Patient(
        hn=hn,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        gender=gender,
    )
    print(f"Patient added successfully. Patient ID: {patient.patient_id}")


@db_session
def add_visit():
    print("\n--- Add Visit ---")
    hn = read_required("Patient HN: ").upper()
    patient = Patient.get(hn=hn)

    if not patient:
        print("Patient not found.")
        return

    visit_date = read_date("Visit date (YYYY-MM-DD): ")
    ward = read_required("Ward: ")
    visit = Visit(visit_date=visit_date, ward=ward, patient=patient)
    print(f"Visit added successfully. Visit ID: {visit.visit_id}")


@db_session
def add_specimen():
    print("\n--- Add Specimen ---")
    visit_id = read_required("Visit ID: ")

    try:
        visit = Visit[int(visit_id)]
    except (ValueError, ObjectNotFound):
        print("Visit not found.")
        return

    specimen_type = read_required("Specimen type: ")
    collection_date_time = read_datetime("Collection date/time (YYYY-MM-DD HH:MM): ")
    specimen = Specimen(
        specimen_type=specimen_type,
        collection_date_time=collection_date_time,
        visit=visit,
    )
    print(f"Specimen added successfully. Specimen ID: {specimen.specimen_id}")


@db_session
def add_organism():
    print("\n--- Add Organism ---")
    specimen_id = read_required("Specimen ID: ")

    try:
        specimen = Specimen[int(specimen_id)]
    except (ValueError, ObjectNotFound):
        print("Specimen not found.")
        return

    organism_name = read_required("Organism name: ")
    organism = Organism(organism_name=organism_name, specimen=specimen)
    print(f"Organism added successfully. Organism ID: {organism.organism_id}")


@db_session
def record_susceptibility():
    print("\n--- Record Susceptibility ---")
    organism_id = read_required("Organism ID: ")
    staff_id = read_required("Reporter Staff ID: ").upper()

    try:
        organism = Organism[int(organism_id)]
    except (ValueError, ObjectNotFound):
        print("Organism not found.")
        return

    reporter = Reporter.get(staff_id=staff_id)
    if not reporter:
        print("Reporter not found.")
        return

    antibiotic_name = read_required("Antibiotic name: ")
    result = read_result("Result (S/I/R): ")
    mic_value = input("MIC value (optional): ").strip() or None
    report_date = read_date("Report date (YYYY-MM-DD): ")

    susceptibility = Susceptibility(
        antibiotic_name=antibiotic_name,
        result=result,
        mic_value=mic_value,
        report_date=report_date,
        organism=organism,
        reporter=reporter,
    )
    print(f"Susceptibility recorded successfully. Result ID: {susceptibility.sus_id}")


@db_session
def search_by_hn():
    print("\n--- Search by HN ---")
    hn = read_required("HN: ").upper()
    patient = Patient.get(hn=hn)

    if not patient:
        print("Patient not found.")
        return

    print_patient_summary(patient)


@db_session
def search_by_patient_name():
    print("\n--- Search by Patient Name ---")
    keyword = read_required("Enter first or last name: ").lower()
    patients = select(
        p for p in Patient
        if keyword in p.first_name.lower() or keyword in p.last_name.lower()
    )[:]

    if not patients:
        print("No matching patients found.")
        return

    for patient in patients:
        print_patient_summary(patient)

from pony.orm import db_session, select

from models import Patient
from patient_service import print_patient_summary, read_required


@db_session
def display_complete_history():
    print("\n--- Complete Historical AST Records ---")
    hn = read_required("HN: ").upper()
    patient = Patient.get(hn=hn)

    if not patient:
        print("Patient not found.")
        return

    print_patient_summary(patient)

    visits = select(v for v in patient.visits).order_by(lambda v: v.visit_date)[:]
    if not visits:
        print("\nNo visits recorded.")
        return

    for visit in visits:
        print(f"\nVisit {visit.visit_id} | Date: {visit.visit_date} | Ward: {visit.ward}")

        for specimen in visit.specimens.order_by(lambda s: s.collection_date_time):
            print(
                f"  Specimen {specimen.specimen_id} | "
                f"{specimen.specimen_type} | Collected: {specimen.collection_date_time}"
            )

            for organism in specimen.organisms.order_by(lambda o: o.organism_name):
                print(f"    Organism {organism.organism_id} | {organism.organism_name}")

                results = organism.susceptibilities.order_by(
                    lambda s: (s.antibiotic_name, s.report_date)
                )
                for susceptibility in results:
                    mic = susceptibility.mic_value or "-"
                    print(
                        f"      {susceptibility.antibiotic_name}: "
                        f"{susceptibility.result} | MIC: {mic} | "
                        f"Reported: {susceptibility.report_date} | "
                        f"Reporter: {susceptibility.reporter.name}"
                    )

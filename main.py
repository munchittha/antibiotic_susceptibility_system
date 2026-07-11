from analysis_service import resistance_trend_report
from database import init_database
from patient_service import (
    add_organism,
    add_patient,
    add_reporter,
    add_specimen,
    add_visit,
    record_susceptibility,
    search_by_hn,
    search_by_patient_name,
)
from report_service import display_complete_history


def show_menu():
    print("\n===== Antibiotic Susceptibility Reporting System =====")
    print("1. Add Reporter")
    print("2. Add Patient")
    print("3. Add Visit")
    print("4. Add Specimen")
    print("5. Add Organism")
    print("6. Record Susceptibility")
    print("7. Search by HN")
    print("8. Search by Patient Name")
    print("9. Resistance Trend Report")
    print("10. Display Complete Historical AST Records")
    print("11. Exit")


def handle_menu_choice(choice):
    actions = {
        "1": add_reporter,
        "2": add_patient,
        "3": add_visit,
        "4": add_specimen,
        "5": add_organism,
        "6": record_susceptibility,
        "7": search_by_hn,
        "8": search_by_patient_name,
        "9": resistance_trend_report,
        "10": display_complete_history,
    }

    action = actions.get(choice)
    if action:
        action()
    elif choice == "11":
        print("Goodbye.")
        return False
    else:
        print("Invalid choice. Please select a menu number.")

    return True


def main():
    init_database()

    running = True
    while running:
        show_menu()
        choice = input("Select an option: ").strip()
        running = handle_menu_choice(choice)


if __name__ == "__main__":
    main()

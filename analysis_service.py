from collections import defaultdict

from pony.orm import db_session, select

from models import Organism, Susceptibility
from patient_service import read_required


def calculate_result_counts(susceptibilities):
    counts = defaultdict(lambda: {"S": 0, "I": 0, "R": 0})
    for susceptibility in susceptibilities:
        counts[susceptibility.antibiotic_name][susceptibility.result] += 1
    return counts


def calculate_resistance_percentages(susceptibilities):
    totals = defaultdict(lambda: {"total": 0, "resistant": 0})
    for susceptibility in susceptibilities:
        organism_name = susceptibility.organism.organism_name
        totals[organism_name]["total"] += 1
        if susceptibility.result == "R":
            totals[organism_name]["resistant"] += 1

    percentages = {}
    for organism_name, values in totals.items():
        percentages[organism_name] = (values["resistant"] / values["total"]) * 100
    return percentages


def get_top_resistant_antibiotics(organism_name):
    susceptibilities = select(
        s for s in Susceptibility
        if s.organism.organism_name.lower() == organism_name.lower()
    )[:]

    antibiotic_totals = defaultdict(lambda: {"total": 0, "resistant": 0})
    for susceptibility in susceptibilities:
        antibiotic = susceptibility.antibiotic_name
        antibiotic_totals[antibiotic]["total"] += 1
        if susceptibility.result == "R":
            antibiotic_totals[antibiotic]["resistant"] += 1

    ranked = []
    for antibiotic, values in antibiotic_totals.items():
        percentage = (values["resistant"] / values["total"]) * 100
        ranked.append((antibiotic, percentage, values["resistant"], values["total"]))

    return sorted(ranked, key=lambda item: item[1], reverse=True)


@db_session
def resistance_trend_report():
    print("\n--- Resistance Trend Report ---")
    susceptibilities = select(s for s in Susceptibility)[:]

    if not susceptibilities:
        print("No susceptibility results found.")
        return

    print("\nResult counts by antibiotic:")
    counts = calculate_result_counts(susceptibilities)
    for antibiotic in sorted(counts):
        values = counts[antibiotic]
        print(
            f"{antibiotic:<20} "
            f"S: {values['S']:<3} I: {values['I']:<3} R: {values['R']:<3}"
        )

    print("\nOverall resistance percentage by organism:")
    percentages = calculate_resistance_percentages(susceptibilities)
    for organism_name in sorted(percentages):
        print(f"{organism_name:<25} Resistant: {percentages[organism_name]:.1f}%")

    organism_name = read_required("\nShow top resistant antibiotics for organism: ")
    matching_organism = select(
        o for o in Organism if o.organism_name.lower() == organism_name.lower()
    ).first()

    if not matching_organism:
        print("Organism not found.")
        return

    print(f"\n## {matching_organism.organism_name}")
    top_antibiotics = get_top_resistant_antibiotics(matching_organism.organism_name)
    for antibiotic, percentage, resistant_count, total_count in top_antibiotics:
        print(
            f"{antibiotic:<20} Resistant: {percentage:.1f}% "
            f"({resistant_count}/{total_count})"
        )

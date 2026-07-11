"""PonyORM entity models for the reporting system.

Each class below maps to one database table. Relationships are declared with
PonyORM's Required and Set fields so records can be connected naturally.
"""

from datetime import date, datetime

from pony.orm import Database, Optional, PrimaryKey, Required, Set


db = Database()


class Reporter(db.Entity):
    """Laboratory staff member who reports susceptibility results."""

    user_id = PrimaryKey(int, auto=True)
    staff_id = Required(str, unique=True)
    name = Required(str)
    susceptibilities = Set("Susceptibility")


class Patient(db.Entity):
    """Patient demographic record."""

    patient_id = PrimaryKey(int, auto=True)
    hn = Required(str, unique=True)
    first_name = Required(str)
    last_name = Required(str)
    date_of_birth = Required(date)
    gender = Required(str)
    visits = Set("Visit")


class Visit(db.Entity):
    """A single hospital visit for a patient."""

    visit_id = PrimaryKey(int, auto=True)
    visit_date = Required(date)
    ward = Required(str)
    patient = Required(Patient)
    specimens = Set("Specimen")


class Specimen(db.Entity):
    """Clinical specimen collected during a visit."""

    specimen_id = PrimaryKey(int, auto=True)
    specimen_type = Required(str)
    collection_date_time = Required(datetime)
    visit = Required(Visit)
    organisms = Set("Organism")


class Organism(db.Entity):
    """Organism isolated from a clinical specimen."""

    organism_id = PrimaryKey(int, auto=True)
    organism_name = Required(str)
    specimen = Required(Specimen)
    susceptibilities = Set("Susceptibility")


class Susceptibility(db.Entity):
    """Antibiotic susceptibility test result for an organism."""

    sus_id = PrimaryKey(int, auto=True)
    antibiotic_name = Required(str)
    result = Required(str)
    mic_value = Optional(str)
    report_date = Required(date)
    organism = Required(Organism)
    reporter = Required(Reporter)

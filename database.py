"""Database configuration for the Antibiotic Susceptibility Reporting System."""

import os
from pathlib import Path

from .models import db


DATABASE_FILE = Path(
    os.environ.get(
        "DATABASE_FILE",
        str(Path(__file__).with_name("antibiotic_system.sqlite")),
    )
)


def init_database() -> None:
    """Connect PonyORM to SQLite and create tables when needed.

    This function is intentionally small so beginners can see exactly where
    the database file is configured and where PonyORM creates the table mapping.
    """
    if db.provider is None:
        DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)
        db.bind(provider="sqlite", filename=str(DATABASE_FILE), create_db=True)
        db.generate_mapping(create_tables=True)

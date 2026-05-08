from __future__ import annotations

from typing import Generator


def get_db():
    # Replace with actual connection pool / SQLAlchemy session
    raise NotImplementedError("Database connection is not configured yet")


def get_db_session() -> Generator:
    # Placeholder for services that expect a DB session dependency.
    raise NotImplementedError("Database session dependency is not configured yet")


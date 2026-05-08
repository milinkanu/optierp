from __future__ import annotations

from sqlalchemy import create_engine

DATABASE_URL = "postgresql://user:password@localhost/finops"

engine = create_engine(DATABASE_URL)


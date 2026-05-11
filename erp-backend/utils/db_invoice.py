from __future__ import annotations

import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/finops")
engine = create_engine(DATABASE_URL)


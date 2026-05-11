from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import MetaData, Table, create_engine, inspect, select
from sqlalchemy.exc import NoSuchTableError

router = APIRouter(prefix="/inspector", tags=["inspector"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/finops")
engine = create_engine(DATABASE_URL)


def _serialize_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


@router.get("/tables/{table_name}")
async def inspect_table(table_name: str, limit: int = Query(10, ge=1, le=100)):
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        raise HTTPException(status_code=404, detail="Table not found")

    columns = inspector.get_columns(table_name)
    foreign_keys = inspector.get_foreign_keys(table_name)

    schema = [
        {
            "name": col["name"],
            "type": str(col["type"]),
            "nullable": col["nullable"],
            "default": str(col["default"]) if col.get("default") is not None else None,
        }
        for col in columns
    ]

    relationships = [
        {
            "targetTable": fk["referred_table"],
            "localKey": ", ".join(fk.get("constrained_columns", [])),
            "foreignKey": ", ".join(fk.get("referred_columns", [])),
        }
        for fk in foreign_keys
    ]

    metadata = MetaData()
    try:
        table = Table(table_name, metadata, autoload_with=engine)
    except NoSuchTableError:
        raise HTTPException(status_code=404, detail="Table not found")

    stmt = select(table).limit(limit)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    sample_rows = [
        {key: _serialize_value(value) for key, value in row.items()}
        for row in rows
    ]

    return {
        "tableName": table_name,
        "schema": schema,
        "sampleRows": sample_rows,
        "relationships": relationships,
    }


@router.get("/tables/{table_name}/rows")
async def inspect_table_rows(table_name: str, limit: int = Query(10, ge=1, le=100)):
    result = await inspect_table(table_name, limit)
    return result["sampleRows"]

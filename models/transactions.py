from __future__ import annotations

from datetime import date, datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel


class TransactionLine(BaseModel):
    account_id: UUID
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    taxable_amount: float
    tax_rate: float
    tax_amount: float
    total_amount: float


class TransactionCreateRequest(BaseModel):
    txn_type: str
    txn_date: date
    party_id: UUID | None = None
    line_items: List[TransactionLine]
    meta: dict | None = None


class TransactionResponse(BaseModel):
    transaction_id: UUID
    company_id: UUID
    txn_type: str
    txn_number: str
    status: str
    created_at: datetime


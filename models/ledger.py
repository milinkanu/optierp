from __future__ import annotations

from datetime import date, datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, condecimal


class JournalLine(BaseModel):
    account_id: UUID
    entry_type: str
    amount: condecimal(gt=0, max_digits=18, decimal_places=2)
    description: str | None = None
    party_id: UUID | None = None


class JournalCreateRequest(BaseModel):
    journal_type: str
    journal_date: date
    reference: str | None = None
    description: str | None = None
    transaction_id: UUID | None = None
    lines: List[JournalLine]


class JournalResponse(BaseModel):
    journal_id: UUID
    company_id: UUID
    journal_number: str
    status: str
    created_at: datetime


class LedgerEntry(BaseModel):
    ledger_entry_id: UUID
    company_id: UUID
    transaction_id: UUID
    journal_id: UUID | None = None
    entry_type: str
    account_id: UUID
    amount: float
    currency: str
    entry_date: date
    reference: str | None = None
    party_id: UUID | None = None
    is_reversal: bool
    created_at: datetime


class ReversalResponse(BaseModel):
    original_journal_id: UUID
    reversal_journal_id: UUID
    status: str
    created_at: datetime


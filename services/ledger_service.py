from datetime import date, datetime
from typing import List, Annotated
from uuid import UUID, uuid4
import os

from fastapi import FastAPI, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from services.common import TenantContext, get_current_context

DATABASE_URL = "postgresql://user:password@localhost/finops"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(title='FinOps Ledger Service')


class JournalLine(BaseModel):
    account_id: UUID
    entry_type: str
    amount: Annotated[float, Field(gt=0)]
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


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post('/ledger/journals', response_model=JournalResponse)
async def create_journal_entry(
    payload: JournalCreateRequest,
    idempotency_key: UUID = Header(..., alias='Idempotency-Key'),
    current_context: TenantContext = Depends(get_current_context)
):
    journal_id = uuid4()
    journal_number = f"JRN-{payload.journal_date.year}-{str(uuid4())[:8]}"
    created_at = datetime.utcnow()

    if os.getenv('FINOPS_USE_DATABASE', '').lower() != 'true':
        return JournalResponse(
            journal_id=journal_id,
            company_id=current_context.company_id,
            journal_number=journal_number,
            status='posted',
            created_at=created_at
        )

    if len(payload.lines) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Journal entry must contain at least two lines')

    total_debit = sum(line.amount for line in payload.lines if line.entry_type == 'debit')
    total_credit = sum(line.amount for line in payload.lines if line.entry_type == 'credit')
    if total_debit != total_credit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Journal entry is not balanced')

    with engine.begin() as conn:
        # Idempotency protection table should be implemented in production.
        conn.execute(
            text(
                "INSERT INTO journal_entries (journal_id, company_id, journal_number, journal_type, journal_date, description, reference, transaction_id, status, created_by, updated_by, created_at, updated_at)"
                " VALUES (:journal_id, :company_id, :journal_number, :journal_type, :journal_date, :description, :reference, :transaction_id, 'posted', :created_by, :updated_by, :created_at, :updated_at)"
            ),
            {
                'journal_id': str(journal_id),
                'company_id': str(current_context.company_id),
                'journal_number': journal_number,
                'journal_type': payload.journal_type,
                'journal_date': payload.journal_date,
                'description': payload.description,
                'reference': payload.reference,
                'transaction_id': str(payload.transaction_id) if payload.transaction_id else None,
                'created_by': str(current_context.user_id),
                'updated_by': str(current_context.user_id),
                'created_at': created_at,
                'updated_at': created_at
            }
        )

        for line in payload.lines:
            conn.execute(
                text(
                    "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at)"
                    " VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, :entry_type, :amount, :description, :party_id, :created_at)"
                ),
                {
                    'journal_id': str(journal_id),
                    'company_id': str(current_context.company_id),
                    'account_id': str(line.account_id),
                    'entry_type': line.entry_type,
                    'amount': line.amount,
                    'description': line.description,
                    'party_id': str(line.party_id) if line.party_id else None,
                    'created_at': created_at
                }
            )

    return JournalResponse(
        journal_id=journal_id,
        company_id=current_context.company_id,
        journal_number=journal_number,
        status='posted',
        created_at=created_at
    )


@app.get('/ledger/entries', response_model=List[LedgerEntry])
async def list_ledger_entries(
    account_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    current_context: TenantContext = Depends(get_current_context)
):
    filters = ["company_id = :company_id"]
    params = {'company_id': str(current_context.company_id)}
    if account_id:
        filters.append("account_id = :account_id")
        params['account_id'] = str(account_id)
    if start_date:
        filters.append("entry_date >= :start_date")
        params['start_date'] = str(start_date)
    if end_date:
        filters.append("entry_date <= :end_date")
        params['end_date'] = str(end_date)

    query = "SELECT * FROM ledger_entries WHERE " + " AND ".join(filters) + " ORDER BY entry_date DESC LIMIT 250"
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [LedgerEntry(**row._mapping) for row in result.fetchall()]


@app.post('/ledger/journals/{journal_id}/reverse', response_model=ReversalResponse)
async def reverse_journal_entry(
    journal_id: UUID,
    current_context: TenantContext = Depends(get_current_context)
):
    reversal_journal_id = uuid4()
    created_at = datetime.utcnow()

    with engine.begin() as conn:
        original = conn.execute(
            text("SELECT journal_id, journal_date, transaction_id FROM journal_entries WHERE company_id = :company_id AND journal_id = :journal_id"),
            {'company_id': str(current_context.company_id), 'journal_id': str(journal_id)}
        ).fetchone()
        if original is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Original journal not found')

        original_data = original._mapping
        conn.execute(
            text(
                "INSERT INTO journal_entries (journal_id, company_id, journal_number, journal_type, journal_date, description, reference, transaction_id, status, created_by, updated_by, created_at, updated_at)"
                " VALUES (:journal_id, :company_id, :journal_number, 'reversal', :journal_date, :description, :reference, :transaction_id, 'posted', :created_by, :updated_by, :created_at, :updated_at)"
            ),
            {
                'journal_id': str(reversal_journal_id),
                'company_id': str(current_context.company_id),
                'journal_number': f"REV-{str(uuid4())[:8]}",
                'journal_date': original_data['journal_date'],
                'description': 'Reversal of journal ' + str(journal_id),
                'reference': str(journal_id),
                'transaction_id': original_data['transaction_id'],
                'created_by': str(current_context.user_id),
                'updated_by': str(current_context.user_id),
                'created_at': created_at,
                'updated_at': created_at
            }
        )

        rows = conn.execute(
            text("SELECT account_id, entry_type, amount, description, party_id FROM journal_entry_lines WHERE journal_id = :journal_id"),
            {'journal_id': str(journal_id)}
        ).fetchall()
        if not rows:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Original journal has no lines to reverse')

        for row in rows:
            row_data = row._mapping
            reversed_type = 'debit' if row_data['entry_type'] == 'credit' else 'credit'
            conn.execute(
                text(
                    "INSERT INTO journal_entry_lines (journal_line_id, journal_id, company_id, account_id, entry_type, amount, description, party_id, created_at)"
                    " VALUES (gen_random_uuid(), :journal_id, :company_id, :account_id, :entry_type, :amount, :description, :party_id, :created_at)"
                ),
                {
                    'journal_id': str(reversal_journal_id),
                    'company_id': str(current_context.company_id),
                    'account_id': str(row_data['account_id']),
                    'entry_type': reversed_type,
                    'amount': row_data['amount'],
                    'description': row_data['description'],
                    'party_id': str(row_data['party_id']) if row_data['party_id'] else None,
                    'created_at': created_at
                }
            )

    return ReversalResponse(
        original_journal_id=journal_id,
        reversal_journal_id=reversal_journal_id,
        status='reversed',
        created_at=created_at
    )

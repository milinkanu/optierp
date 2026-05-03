from datetime import date, datetime
from uuid import UUID, uuid4
from typing import List

from fastapi import FastAPI, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from services.common import TenantContext, get_current_context

app = FastAPI(title='FinOps Transaction Service')


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


@app.post('/transactions', response_model=TransactionResponse)
async def create_transaction(
    payload: TransactionCreateRequest,
    idempotency_key: UUID = Header(..., alias='Idempotency-Key'),
    current_context: TenantContext = Depends(get_current_context)
):
    # Example idempotency handling is required here.
    # This skeleton does not include DB state management.
    transaction_id = uuid4()
    txn_number = f"{payload.txn_type[:3].upper()}-{payload.txn_date.year}-{str(uuid4())[:8]}"

    # TODO: Insert into transactions, transaction_items, ledger_entries, api_idempotency_keys, audit_logs, outbox in one DB transaction.

    return TransactionResponse(
        transaction_id=transaction_id,
        company_id=current_context.company_id,
        txn_type=payload.txn_type,
        txn_number=txn_number,
        status='posted',
        created_at=datetime.utcnow()
    )


@app.get('/transactions/{transaction_id}', response_model=TransactionResponse)
async def get_transaction(transaction_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    # Replace with database lookup by company_id and transaction_id.
    return TransactionResponse(
        transaction_id=transaction_id,
        company_id=current_context.company_id,
        txn_type='sales_invoice',
        txn_number='INV-0001',
        status='posted',
        created_at=datetime.utcnow()
    )


@app.post('/transactions/{transaction_id}/reverse')
async def reverse_transaction(transaction_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    # Insert reversal entries. The original transaction remains immutable.
    return {
        'transaction_id': transaction_id,
        'reversal_id': str(uuid4()),
        'status': 'reversed'
    }

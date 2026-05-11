from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header

from models.transactions import TransactionCreateRequest, TransactionResponse
from utils.auth import TenantContext, get_current_context

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse)
async def create_transaction(
    payload: TransactionCreateRequest,
    idempotency_key: UUID = Header(..., alias="Idempotency-Key"),
    current_context: TenantContext = Depends(get_current_context),
):
    transaction_id = uuid4()
    txn_number = f"{payload.txn_type[:3].upper()}-{payload.txn_date.year}-{str(uuid4())[:8]}"
    return TransactionResponse(
        transaction_id=transaction_id,
        company_id=current_context.company_id,
        txn_type=payload.txn_type,
        txn_number=txn_number,
        status="posted",
        created_at=datetime.utcnow(),
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    return TransactionResponse(
        transaction_id=transaction_id,
        company_id=current_context.company_id,
        txn_type="sales_invoice",
        txn_number="INV-0001",
        status="posted",
        created_at=datetime.utcnow(),
    )


@router.post("/{transaction_id}/reverse")
async def reverse_transaction(transaction_id: UUID, current_context: TenantContext = Depends(get_current_context)):
    return {"transaction_id": transaction_id, "reversal_id": str(uuid4()), "status": "reversed"}


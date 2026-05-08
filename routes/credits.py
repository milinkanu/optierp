from __future__ import annotations

from fastapi import APIRouter, Depends

from models.ocr import CreditBalanceResponse
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session
from utils.ocr_processing import get_credit_balance

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_credit_balance_endpoint(current_context: TenantContext = Depends(get_current_context), db=Depends(get_db_session)):
    balance = await get_credit_balance(db, current_context.company_id)
    return CreditBalanceResponse(company_id=current_context.company_id, credit_balance=balance)


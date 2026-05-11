from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from models.auth import CompanyCreateRequest
from utils.auth import TenantContext, get_current_context

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("")
async def create_company(payload: CompanyCreateRequest):
    return {"company_id": str(uuid4()), "company_name": payload.company_name, "created_at": date.today().isoformat()}


@router.post("/{company_id}/bank-accounts")
async def add_bank_account(company_id: UUID, payload: dict, current_context: TenantContext = Depends(get_current_context)):
    if str(current_context.company_id) != str(company_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    return {"bank_account_id": str(uuid4()), "company_id": str(company_id)}


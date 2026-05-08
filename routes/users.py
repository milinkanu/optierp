from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends

from models.auth import UserCreateRequest
from utils.auth import TenantContext, get_current_context

router = APIRouter(prefix="/users", tags=["users"])


@router.post("")
async def create_user(payload: UserCreateRequest, current_context: TenantContext = Depends(get_current_context)):
    return {"user_id": str(uuid4()), "company_id": str(current_context.company_id), "email": payload.email}


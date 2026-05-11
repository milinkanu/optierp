from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends

from models.auth import LoginRequest, LoginResponse
from utils.auth import TenantContext, create_access_token, get_current_context

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    user_id = uuid4()
    company_id = uuid4()
    user_version = 1
    roles = ["owner"]
    delegations = []

    access_token = create_access_token(
        subject=str(user_id),
        company_id=company_id,
        user_version=user_version,
        roles=roles,
        delegations=delegations,
    )
    return LoginResponse(access_token=access_token)


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(current_context: TenantContext = Depends(get_current_context)):
    token = create_access_token(
        subject=str(current_context.user_id),
        company_id=current_context.company_id,
        user_version=1,
        roles=current_context.roles,
        delegations=[],
    )
    return LoginResponse(access_token=token)


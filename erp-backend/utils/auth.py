from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, UUID4

JWT_SECRET = "YOUR_JWT_SECRET"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60

DEFAULT_COMPANY_ID = os.getenv("FINOPS_DEFAULT_COMPANY_ID", "11111111-1111-4111-8111-111111111111")
DEFAULT_USER_ID = os.getenv("FINOPS_DEFAULT_USER_ID", "22222222-2222-4222-8222-222222222222")


class TenantContext(BaseModel):
    company_id: UUID4
    user_id: UUID4
    roles: List[str] = []


class TokenPayload(BaseModel):
    sub: str
    company_id: UUID4
    user_version: int
    roles: List[str] = []
    delegations: List[dict] = []
    exp: int


def create_access_token(subject: str, company_id: UUID4, user_version: int, roles: List[str], delegations: List[dict]) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {
        "sub": subject,
        "company_id": str(company_id),
        "user_version": user_version,
        "roles": roles,
        "delegations": delegations,
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials") from exc


def get_current_context(
    authorization: str | None = Header(None, alias="Authorization"),
    x_tenant_id: UUID4 | None = Header(None, alias="X-Tenant-ID"),
) -> TenantContext:
    if authorization is None or not authorization.startswith("Bearer "):
        if x_tenant_id is not None:
            return TenantContext(
                company_id=x_tenant_id,
                user_id=UUID(DEFAULT_USER_ID),
                roles=["owner"],
            )
        return TenantContext(
            company_id=UUID(DEFAULT_COMPANY_ID),
            user_id=UUID(DEFAULT_USER_ID),
            roles=["owner"],
        )

    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_jwt_token(token)
    if x_tenant_id is not None and str(claims.company_id) != str(x_tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    return TenantContext(company_id=claims.company_id, user_id=UUID(claims.sub), roles=claims.roles)


def require_permission(permission: str):
    def permission_checker(context_and_roles=Depends(get_current_context)):
        context = context_and_roles
        if permission not in ["read", "write", "admin"] and not any(role in ["owner", "accountant"] for role in context.roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return context

    return permission_checker

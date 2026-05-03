from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Security, status
from jose import JWTError, jwt
from pydantic import BaseModel, UUID4

JWT_SECRET = 'YOUR_JWT_SECRET'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_MINUTES = 60

class TenantContext(BaseModel):
    company_id: UUID4
    user_id: UUID4
    roles: List[str] = []

class TokenPayload(BaseModel):
    sub: str
    company_id: UUID4
    user_version: int
    roles: List[str] = []
    delegations: List[dict] = []  # List of active delegations
    exp: int


def create_access_token(subject: str, company_id: UUID4, user_version: int, roles: List[str], delegations: List[dict]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {
        'sub': subject,
        'company_id': str(company_id),
        'user_version': user_version,
        'roles': roles,
        'delegations': delegations,
        'exp': int(expire.timestamp())
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authentication credentials') from exc


def get_current_context(
    authorization: str = Header(..., alias='Authorization'),
    x_tenant_id: UUID4 = Header(..., alias='X-Tenant-ID')
) -> TenantContext:
    if not authorization.startswith('Bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid authorization header')
    token = authorization.removeprefix('Bearer ').strip()
    claims = verify_jwt_token(token)
    if str(claims.company_id) != str(x_tenant_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant mismatch')
    # Note: In production, verify user_version and delegations against DB here
    return TenantContext(company_id=claims.company_id, user_id=UUID(claims.sub), roles=claims.roles)


def require_permission(permission: str):
    def permission_checker(context: TenantContext = Depends(get_current_context)) -> TenantContext:
        # In production, check permissions based on roles and delegations
        # For now, assume roles have permissions
        if permission not in ['read', 'write', 'admin'] and not any(role in ['owner', 'accountant'] for role in context.roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Insufficient permissions')
        return context
    return permission_checker


def get_db():
    # Replace with actual connection pool / SQLAlchemy session
    raise NotImplementedError('Database connection is not configured yet')

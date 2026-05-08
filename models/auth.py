from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"


class CompanyCreateRequest(BaseModel):
    company_name: str
    trade_name: str | None = None
    company_type: str
    pan: str
    gstin: str | None = None
    tan: str | None = None
    udyam_no: str | None = None
    gst_type: str
    primary_state: str
    extra_states: list[str] | None = []


class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str
    password: str
    roles: list[str] = []


class DelegationCreateRequest(BaseModel):
    delegate_email: EmailStr
    role_name: str
    start_date: date
    end_date: date


class DelegationResponse(BaseModel):
    delegation_id: UUID
    delegate_user_id: UUID
    role_name: str
    start_date: date
    end_date: date
    is_active: bool


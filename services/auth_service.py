from datetime import date
from uuid import UUID, uuid4

from fastapi import FastAPI, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr

from services.common import TenantContext, create_access_token, get_current_context

app = FastAPI(title='FinOps Auth Service')


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = 'Bearer'


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


@app.post('/auth/login', response_model=LoginResponse)
async def login(payload: LoginRequest):
    # TODO: Replace with real database lookup
    # user = db.query(users).filter(users.email == payload.email).first()
    # if not verify_password(payload.password, user.password_hash):
    #     raise HTTPException(status_code=401, detail='Invalid credentials')
    # if not user.is_active:
    #     raise HTTPException(status_code=403, detail='User inactive')
    # roles = db.execute(select(app.get_effective_roles(user.user_id))).scalars().all()
    # delegations = db.query(delegations).filter(
    #     delegations.delegate_user_id == user.user_id,
    #     delegations.is_active == True,
    #     func.now().between(delegations.start_date, delegations.end_date)
    # ).all()
    # delegations_list = [{'role': d.role.name, 'end_date': d.end_date.isoformat()} for d in delegations]

    # Mock data
    user_id = uuid4()
    company_id = uuid4()
    user_version = 1
    roles = ['owner']
    delegations = []

    access_token = create_access_token(
        subject=str(user_id),
        company_id=company_id,
        user_version=user_version,
        roles=roles,
        delegations=delegations
    )
    return LoginResponse(access_token=access_token)


@app.post('/auth/refresh', response_model=LoginResponse)
async def refresh_token(current_context: TenantContext = Depends(get_current_context)):
    token = create_access_token(
        subject=str(current_context.user_id),
        company_id=current_context.company_id,
        user_version=1,
        roles=current_context.roles,
        delegations=[]
    )
    return LoginResponse(access_token=token)


@app.post('/companies')
async def create_company(payload: CompanyCreateRequest):
    # Insert tenant onboarding workflow here.
    return {
        'company_id': str(uuid4()),
        'company_name': payload.company_name,
        'created_at': date.today().isoformat()
    }


@app.post('/companies/{company_id}/bank-accounts')
async def add_bank_account(company_id: UUID, payload: dict, current_context: TenantContext = Depends(get_current_context)):
    if str(current_context.company_id) != str(company_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Tenant mismatch')
    return {'bank_account_id': str(uuid4()), 'company_id': str(company_id)}


@app.post('/users')
async def create_user(payload: UserCreateRequest, current_context: TenantContext = Depends(get_current_context)):
    return {'user_id': str(uuid4()), 'company_id': str(current_context.company_id), 'email': payload.email}

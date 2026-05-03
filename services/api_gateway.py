from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from services.common import get_current_context, TenantContext
from uuid import UUID

app = FastAPI(title='FinOps API Gateway')


@app.get('/health')
async def health_check():
    return {'status': 'ok'}


@app.middleware('http')
async def tenant_middleware(request: Request, call_next):
    if request.url.path.startswith('/health'):
        return await call_next(request)

    try:
        company_id_str = request.headers.get('X-Tenant-ID')
        if not company_id_str:
            raise ValueError("Missing X-Tenant-ID")
        company_id = UUID(company_id_str)

        user_id_str = request.headers.get('X-User-ID')
        if not user_id_str:
            raise ValueError("Missing X-User-ID")
        user_id = UUID(user_id_str)

        roles_str = request.headers.get('X-User-Roles')
        roles = roles_str.split(',') if roles_str else []

        request.state.tenant_context = TenantContext(
            company_id=company_id,
            user_id=user_id,
            roles=roles
        )
    except Exception:
        return JSONResponse({'detail': 'Missing or invalid tenant headers'}, status_code=status.HTTP_401_UNAUTHORIZED)

    response = await call_next(request)
    return response


@app.post('/proxy/{service_name}/{path:path}')
async def proxy_request(service_name: str, path: str, request: Request):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail='Gateway proxy is not implemented in skeleton mode')


@app.get('/services')
async def list_services():
    return {
        'services': [
            'auth-service',
            'transaction-service',
            'ledger-service',
            'ocr-service',
            'compliance-service',
            'bank-reconciliation-service'
        ]
    }

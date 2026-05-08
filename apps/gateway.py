from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from routes.health import router as health_router
from routes.proxy import router as proxy_router
from routes.services_registry import router as services_registry_router
from utils.auth import TenantContext


def create_app() -> FastAPI:
    app = FastAPI(title="FinOps API Gateway")

    @app.middleware("http")
    async def tenant_middleware(request: Request, call_next):
        if request.url.path.startswith("/health"):
            return await call_next(request)

        try:
            TenantContext(
                company_id=request.headers.get("X-Tenant-ID"),
                user_id=request.headers.get("X-User-ID"),
                roles=request.headers.get("X-User-Roles", "").split(",") if request.headers.get("X-User-Roles") else [],
            )
        except Exception:
            return JSONResponse({"detail": "Missing or invalid tenant headers"}, status_code=status.HTTP_401_UNAUTHORIZED)

        return await call_next(request)

    app.include_router(health_router)
    app.include_router(proxy_router)
    app.include_router(services_registry_router)
    return app


app = create_app()

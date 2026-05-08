from __future__ import annotations

from fastapi import FastAPI

from routes.auth import router as auth_router
from routes.companies import router as companies_router
from routes.users import router as users_router


def create_app() -> FastAPI:
    app = FastAPI(title="FinOps Auth Service")
    app.include_router(auth_router)
    app.include_router(companies_router)
    app.include_router(users_router)
    return app


app = create_app()


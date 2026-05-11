from __future__ import annotations

from fastapi import FastAPI

from routes.compliance import router as compliance_router


def create_app() -> FastAPI:
    app = FastAPI(title="FinOps Compliance Service")
    app.include_router(compliance_router)
    return app


app = create_app()


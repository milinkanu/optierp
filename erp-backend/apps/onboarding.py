from __future__ import annotations

from fastapi import FastAPI

from routes.onboarding import router as onboarding_router


def create_app() -> FastAPI:
    app = FastAPI(title="FinOps Onboarding Service")
    app.include_router(onboarding_router)
    return app


app = create_app()


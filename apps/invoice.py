from __future__ import annotations

from fastapi import FastAPI

from routes.invoices import router as invoices_router


def create_app() -> FastAPI:
    app = FastAPI(title="FinOps Invoice Service")
    app.include_router(invoices_router)
    return app


app = create_app()


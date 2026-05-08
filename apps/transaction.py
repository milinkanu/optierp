from __future__ import annotations

from fastapi import FastAPI

from routes.transactions import router as transactions_router


def create_app() -> FastAPI:
    app = FastAPI(title="FinOps Transaction Service")
    app.include_router(transactions_router)
    return app


app = create_app()


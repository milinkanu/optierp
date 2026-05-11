from __future__ import annotations

from fastapi import FastAPI

from routes.ledger import router as ledger_router


def create_app() -> FastAPI:
    app = FastAPI(title="FinOps Ledger Service")
    app.include_router(ledger_router)
    return app


app = create_app()


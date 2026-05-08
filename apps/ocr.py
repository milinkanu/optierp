from __future__ import annotations

from fastapi import FastAPI

from routes.credits import router as credits_router
from routes.documents import router as documents_router
from routes.ocr import router as ocr_router


def create_app() -> FastAPI:
    app = FastAPI(title="FinOps OCR Service")
    app.include_router(documents_router)
    app.include_router(ocr_router)
    app.include_router(credits_router)
    return app


app = create_app()


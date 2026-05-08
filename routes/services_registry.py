from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["services"])


@router.get("/services")
async def list_services():
    return {
        "services": [
            "auth-service",
            "transaction-service",
            "ledger-service",
            "ocr-service",
            "compliance-service",
            "bank-reconciliation-service",
        ]
    }


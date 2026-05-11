from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.post("/{service_name}/{path:path}")
async def proxy_request(service_name: str, path: str, request: Request):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Gateway proxy is not implemented in skeleton mode",
    )


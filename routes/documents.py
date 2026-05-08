from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, Depends, File, UploadFile

from models.ocr import DocumentResponse, DocumentType, OCRMode
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session
from utils.ocr_processing import save_document
from routes.ocr import process_ocr_async

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    document_type: DocumentType,
    mode: OCRMode,
    file: UploadFile = File(...),
    current_context: TenantContext = Depends(get_current_context),
    db=Depends(get_db_session),
):
    file_path = f"/tmp/{uuid4()}_{file.filename}"
    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    checksum = "placeholder_checksum"
    file_url = f"s3://bucket/{uuid4()}_{file.filename}"

    document_id = uuid4()
    await save_document(db, current_context.company_id, document_type, file.filename, file_url, len(content), checksum, current_context.user_id)

    if mode != OCRMode.MANUAL:
        asyncio.create_task(process_ocr_async(document_id, mode, file_path, current_context, db))

    return DocumentResponse(
        document_id=document_id,
        company_id=current_context.company_id,
        document_type=document_type,
        file_name=file.filename,
        file_url=file_url,
        uploaded_at=datetime.utcnow(),
    )


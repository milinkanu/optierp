from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends

from models.ocr import ConfirmOCRRequest, OCRMode, OCRProcessRequest, OCRResultResponse
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session
from utils.ocr_processing import (
    cleanup_temp_file,
    deduct_credit,
    get_credit_balance,
    process_paddleocr,
    process_vlm,
    save_ocr_result,
)

router = APIRouter(prefix="/ocr", tags=["ocr"])


async def process_ocr_async(document_id: UUID, mode: OCRMode, file_path: str, context: TenantContext, db):
    try:
        extracted_data = {}
        paddle_conf = None
        vlm_conf = None
        result_status = "scanned"

        if mode in [OCRMode.OCR, OCRMode.SMART]:
            extracted_data, paddle_conf = await process_paddleocr(file_path)

        if mode == OCRMode.SMART and (paddle_conf is None or paddle_conf < 0.85):
            balance = await get_credit_balance(db, context.company_id)
            if balance < 1.0:
                result_status = "failed"
                extracted_data = {"error": "Insufficient credits for VLM processing"}
            else:
                await deduct_credit(db, context.company_id, 1.0, "ocr_result", document_id, "VLM processing", context.user_id)
                vlm_data, vlm_conf = await process_vlm(file_path)
                extracted_data.update(vlm_data)

        if paddle_conf and paddle_conf >= 0.85:
            result_status = "confirmed"
        elif vlm_conf and vlm_conf >= 0.85:
            result_status = "confirmed"
        else:
            result_status = "pending"

        await save_ocr_result(db, document_id, context.company_id, mode, paddle_conf, vlm_conf, extracted_data, result_status)
    except Exception as exc:
        await save_ocr_result(db, document_id, context.company_id, mode, None, None, {"error": str(exc)}, "failed")
    finally:
        cleanup_temp_file(file_path)


@router.post("/process", response_model=OCRResultResponse)
async def process_ocr(
    request: OCRProcessRequest,
    current_context: TenantContext = Depends(get_current_context),
    db=Depends(get_db_session),
):
    file_path = "/tmp/placeholder"
    await process_ocr_async(request.document_id, request.mode, file_path, current_context, db)
    return OCRResultResponse(
        ocr_result_id=uuid4(),
        document_id=request.document_id,
        company_id=current_context.company_id,
        mode=request.mode,
        paddleocr_confidence=0.9,
        vlm_confidence=None,
        extracted_data={},
        status="processed",
        processed_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )


@router.patch("/{ocr_result_id}/confirm")
async def confirm_ocr_result(
    ocr_result_id: UUID,
    request: ConfirmOCRRequest,
    current_context: TenantContext = Depends(get_current_context),
    db=Depends(get_db_session),
):
    return {"ocr_result_id": ocr_result_id, "status": "confirmed"}


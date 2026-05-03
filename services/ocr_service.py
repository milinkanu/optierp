from datetime import datetime
from uuid import UUID, uuid4
import asyncio
import hashlib
import os
import tempfile
from enum import Enum
from typing import Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
import aiofiles

from services.common import TenantContext, get_current_context

# Assuming OCR libraries are installed
try:
    from paddleocr import PaddleOCR
    ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
except Exception:
    ocr_engine = None

# Placeholder for VLM
class VLMEngine:
    async def extract(self, image_path: str) -> Dict[str, Any]:
        # Placeholder implementation
        return {"vlm_data": "placeholder", "confidence": 0.9}

vlm_engine = VLMEngine()

app = FastAPI(title='FinOps OCR Service')

DOCUMENT_STORE: dict[UUID, dict[str, Any]] = {}
OCR_RESULT_STORE: dict[UUID, dict[str, Any]] = {}
DOCUMENT_RESULT_INDEX: dict[UUID, UUID] = {}

# Enums
class OCRMode(str, Enum):
    MANUAL = 'manual'
    OCR = 'ocr'
    SMART = 'smart'

class DocumentType(str, Enum):
    INVOICE = 'invoice'
    RECEIPT = 'receipt'
    BANK_STATEMENT = 'bank_statement'
    KYC = 'kyc'
    OTHER = 'other'

# Models
class DocumentUploadRequest(BaseModel):
    document_type: DocumentType
    mode: OCRMode

class DocumentResponse(BaseModel):
    document_id: UUID
    company_id: UUID
    document_type: DocumentType
    file_name: str
    file_url: str
    uploaded_at: datetime

class OCRProcessRequest(BaseModel):
    document_id: UUID
    mode: OCRMode

class OCRResultResponse(BaseModel):
    ocr_result_id: UUID
    document_id: UUID
    company_id: UUID
    mode: OCRMode
    paddleocr_confidence: Optional[float] = None
    vlm_confidence: Optional[float] = None
    extracted_data: Dict[str, Any]
    status: str
    processed_at: Optional[datetime] = None
    created_at: datetime
    error_message: Optional[str] = None

class CreditBalanceResponse(BaseModel):
    company_id: UUID
    credit_balance: float

class ConfirmOCRRequest(BaseModel):
    ocr_result_id: Optional[UUID] = None
    extracted_data: Dict[str, Any]

# Database models (assuming SQLAlchemy)
# Note: In real implementation, define proper SQLAlchemy models

async def save_document(document_id: UUID, company_id: UUID, document_type: str, file_name: str, file_url: str, file_size: int, checksum: str, uploaded_by: UUID, local_path: str):
    DOCUMENT_STORE[document_id] = {
        'document_id': document_id,
        'company_id': company_id,
        'document_type': document_type,
        'file_name': file_name,
        'file_url': file_url,
        'file_size': file_size,
        'checksum': checksum,
        'uploaded_by': uploaded_by,
        'local_path': local_path,
        'uploaded_at': datetime.utcnow()
    }

async def save_ocr_result(document_id: UUID, company_id: UUID, mode: str, paddle_conf: Optional[float], vlm_conf: Optional[float], extracted_data: Dict, status: str, error_message: Optional[str] = None) -> OCRResultResponse:
    ocr_result_id = DOCUMENT_RESULT_INDEX.get(document_id, uuid4())
    now = datetime.utcnow()
    existing = OCR_RESULT_STORE.get(ocr_result_id, {})
    result = OCRResultResponse(
        ocr_result_id=ocr_result_id,
        document_id=document_id,
        company_id=company_id,
        mode=mode,
        paddleocr_confidence=paddle_conf,
        vlm_confidence=vlm_conf,
        extracted_data=extracted_data,
        status=status,
        processed_at=now if status in {'processed', 'confirmed', 'pending', 'failed'} else None,
        created_at=existing.get('created_at', now),
        error_message=error_message
    )
    OCR_RESULT_STORE[ocr_result_id] = result.model_dump()
    DOCUMENT_RESULT_INDEX[document_id] = ocr_result_id
    return result

async def get_credit_balance(company_id: UUID) -> float:
    # Placeholder
    return 100.0  # Assume 100 credits

async def deduct_credit(company_id: UUID, amount: float, ref_type: str, ref_id: UUID, description: str, actor: UUID):
    # Placeholder
    pass

async def process_paddleocr(image_path: str) -> tuple[Dict[str, Any], float]:
    if not ocr_engine:
        raise HTTPException(status_code=500, detail="PaddleOCR not available")
    results = ocr_engine.ocr(image_path, cls=True)
    # Process results to extract structured data
    extracted = {}
    confidence = 0.9  # Calculate average confidence
    return extracted, confidence

async def process_vlm(image_path: str) -> tuple[Dict[str, Any], float]:
    result = await vlm_engine.extract(image_path)
    return result, result.get('confidence', 0.9)

@app.post('/documents/upload', response_model=DocumentResponse)
async def upload_document(
    document_type: DocumentType,
    mode: OCRMode,
    file: UploadFile = File(...),
    current_context: TenantContext = Depends(get_current_context)
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Uploaded file must have a filename')

    filename = file.filename
    # Save file to storage (placeholder)
    file_path = os.path.join(tempfile.gettempdir(), f"{uuid4()}_{filename}")
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    checksum = hashlib.sha256(content).hexdigest()
    file_url = f"s3://bucket/{uuid4()}_{filename}"

    document_id = uuid4()
    await save_document(document_id, current_context.company_id, document_type, filename, file_url, len(content), checksum, current_context.user_id, file_path)

    # If mode is not manual, trigger OCR processing
    if mode != OCRMode.MANUAL:
        asyncio.create_task(process_ocr_async(document_id, mode, file_path, current_context, cleanup_file=True))

    return DocumentResponse(
        document_id=document_id,
        company_id=current_context.company_id,
        document_type=document_type,
        file_name=file.filename,
        file_url=file_url,
        uploaded_at=datetime.utcnow()
    )

async def process_ocr_async(document_id: UUID, mode: OCRMode, file_path: str, context: TenantContext, cleanup_file: bool = False) -> OCRResultResponse:
    try:
        extracted_data = {}
        paddle_conf = None
        vlm_conf = None
        status = 'scanned'

        if mode in [OCRMode.OCR, OCRMode.SMART]:
            extracted_data, paddle_conf = await process_paddleocr(file_path)

        if mode == OCRMode.SMART and (paddle_conf is None or paddle_conf < 0.85):
            # Check credits
            balance = await get_credit_balance(context.company_id)
            if balance < 1.0:  # Assume 1 credit per VLM call
                status = 'failed'
                extracted_data = {"error": "Insufficient credits for VLM processing"}
            else:
                await deduct_credit(context.company_id, 1.0, 'ocr_result', document_id, 'VLM processing', context.user_id)
                vlm_data, vlm_conf = await process_vlm(file_path)
                extracted_data.update(vlm_data)

        if paddle_conf and paddle_conf >= 0.85:
            status = 'confirmed'
        elif vlm_conf and vlm_conf >= 0.85:
            status = 'confirmed'
        else:
            status = 'pending'

        return await save_ocr_result(document_id, context.company_id, mode, paddle_conf, vlm_conf, extracted_data, status)

    except Exception as e:
        return await save_ocr_result(document_id, context.company_id, mode, None, None, {"error": str(e)}, 'failed', str(e))
    finally:
        # Cleanup temp file
        if cleanup_file and os.path.exists(file_path):
            os.remove(file_path)

@app.post('/ocr/process', response_model=OCRResultResponse)
async def process_ocr(
    request: OCRProcessRequest,
    current_context: TenantContext = Depends(get_current_context)
):
    document = DOCUMENT_STORE.get(request.document_id)
    if not document or str(document['company_id']) != str(current_context.company_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Document not found')

    file_path = document['local_path']
    if not os.path.exists(file_path):
        return await save_ocr_result(
            request.document_id,
            current_context.company_id,
            request.mode,
            None,
            None,
            {'error': 'Document file is no longer available for OCR processing'},
            'failed',
            'Document file is no longer available for OCR processing'
        )

    return await process_ocr_async(request.document_id, request.mode, file_path, current_context)

@app.get('/credits/balance', response_model=CreditBalanceResponse)
async def get_credit_balance_endpoint(
    current_context: TenantContext = Depends(get_current_context)
):
    balance = await get_credit_balance(current_context.company_id)
    return CreditBalanceResponse(company_id=current_context.company_id, credit_balance=balance)

@app.patch('/ocr/{ocr_result_id}/confirm')
async def confirm_ocr_result(
    ocr_result_id: UUID,
    request: ConfirmOCRRequest,
    current_context: TenantContext = Depends(get_current_context)
):
    result = OCR_RESULT_STORE.get(ocr_result_id)
    if result and str(result['company_id']) != str(current_context.company_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='OCR result not found')
    if result:
        result['extracted_data'] = request.extracted_data
        result['status'] = 'confirmed'
        result['processed_at'] = datetime.utcnow()
    return {"ocr_result_id": ocr_result_id, "status": "confirmed"}

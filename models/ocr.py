from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class OCRMode(str):
    MANUAL = "manual"
    OCR = "ocr"
    SMART = "smart"


class DocumentType(str):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    BANK_STATEMENT = "bank_statement"
    KYC = "kyc"
    OTHER = "other"


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
    paddleocr_confidence: Optional[float]
    vlm_confidence: Optional[float]
    extracted_data: Dict[str, Any]
    status: str
    processed_at: Optional[datetime]
    created_at: datetime


class CreditBalanceResponse(BaseModel):
    company_id: UUID
    credit_balance: float


class ConfirmOCRRequest(BaseModel):
    extracted_data: Dict[str, Any]


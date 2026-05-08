from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
import re
import hashlib
import requests
from cryptography.fernet import Fernet

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from services.common import TenantContext, get_current_context

# Database setup (simplified - in production use connection pooling)
DATABASE_URL = "postgresql://user:password@localhost/finops"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

router = APIRouter(tags=["onboarding"])

# Encryption key for PAN (in production use proper key management)
PAN_ENCRYPTION_KEY = Fernet.generate_key()

class APIOnboardingRequest(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15)
    pan: str = Field(..., min_length=10, max_length=10)
    email: EmailStr
    phone: str = Field(..., pattern=r'^\+91[6-9]\d{9}$')

class APIOnboardingResponse(BaseModel):
    company_id: UUID
    status: str
    prefilled_data: dict
    requires_confirmation: bool

class OCRUploadRequest(BaseModel):
    document_type: str  # gst_certificate, pan_card, udyam_certificate, mca_certificate, bank_proof

class OCRUploadResponse(BaseModel):
    kyc_document_id: UUID
    job_id: UUID
    status: str

class OnboardingJobStatus(BaseModel):
    job_id: UUID
    status: str
    extracted_data: Optional[dict] = None
    confidence: Optional[float] = None
    error_message: Optional[str] = None

class OnboardingConfirmationRequest(BaseModel):
    company_data: dict
    kyc_document_ids: List[UUID]

class OnboardingConfirmationResponse(BaseModel):
    company_id: UUID
    onboarding_completed: bool

def validate_gstin_checksum(gstin: str) -> bool:
    """Validate GSTIN checksum"""
    if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin):
        return False

    # GSTIN checksum validation logic
    chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    factor = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1]
    total = 0

    for i in range(14):
        char = gstin[i]
        value = chars.index(char)
        total += value * factor[i]

    check_digit = (11 - (total % 11)) % 11
    expected_check = chars[check_digit] if check_digit < 10 else str(check_digit - 10)

    return gstin[14] == expected_check

def extract_pan_from_gstin(gstin: str) -> str:
    """Extract PAN from GSTIN (positions 2-11)"""
    return gstin[2:12]

def encrypt_pan(pan: str) -> str:
    """Encrypt PAN using Fernet symmetric encryption."""
    f = Fernet(PAN_ENCRYPTION_KEY)
    return f.encrypt(pan.encode()).decode()

def decrypt_pan(encrypted_pan: str) -> str:
    """Decrypt PAN"""
    f = Fernet(PAN_ENCRYPTION_KEY)
    return f.decrypt(encrypted_pan.encode()).decode()

def call_external_api(endpoint: str, data: dict) -> dict:
    """Mock external API call for prefill data"""
    # In production, call actual APIs like GST API, PAN verification API, etc.
    if endpoint == 'gst_details':
        return {
            'company_name': 'Sample Company Pvt Ltd',
            'trade_name': 'Sample Trade',
            'primary_state': 'Maharashtra',
            'gst_type': 'regular'
        }
    elif endpoint == 'pan_verification':
        return {'valid': True, 'name': 'John Doe'}
    return {}

def create_default_roles_and_user(db, company_id: UUID, owner_email: str, owner_name: str):
    """Create default roles and owner user for new company"""
    # Create default roles
    roles = [
        ('owner', 'Company owner with full access'),
        ('accountant', 'Accounting and financial operations'),
        ('auditor', 'Read-only access for auditing'),
        ('employee', 'Basic employee access'),
        ('tax_admin', 'Tax filing and compliance access')
    ]
    
    role_ids = {}
    for role_name, desc in roles:
        role_id = uuid4()
        db.execute(text("""
            INSERT INTO roles (role_id, company_id, name, description)
            VALUES (:role_id, :company_id, :name, :description)
        """), {
            'role_id': role_id,
            'company_id': company_id,
            'name': role_name,
            'description': desc
        })
        role_ids[role_name] = role_id
    
    # Create owner user
    owner_user_id = uuid4()
    password_hash = hashlib.sha256('default_password'.encode()).hexdigest()  # In production, proper hashing
    db.execute(text("""
        INSERT INTO users (user_id, company_id, email, password_hash, name)
        VALUES (:user_id, :company_id, :email, :password_hash, :name)
    """), {
        'user_id': owner_user_id,
        'company_id': company_id,
        'email': owner_email,
        'password_hash': password_hash,
        'name': owner_name
    })
    
    # Assign owner role
    db.execute(text("""
        INSERT INTO user_roles (user_id, role_id)
        VALUES (:user_id, :role_id)
    """), {
        'user_id': owner_user_id,
        'role_id': role_ids['owner']
    })
    
    # Default permissions
    permissions = {
        'owner': ['*'],  # All permissions
        'accountant': ['read:ledger', 'write:transactions', 'read:reports'],
        'auditor': ['read:ledger', 'read:reports'],
        'employee': ['read:basic'],
        'tax_admin': ['read:compliance', 'write:filings']
    }
    
    for role_name, perms in permissions.items():
        for perm in perms:
            db.execute(text("""
                INSERT INTO permissions (role_id, permission)
                VALUES (:role_id, :permission)
            """), {
                'role_id': role_ids[role_name],
                'permission': perm
            })

@router.post('/onboarding/api-prefill', response_model=APIOnboardingResponse)
async def api_based_onboarding(
    payload: APIOnboardingRequest,
    current_context: TenantContext = Depends(get_current_context)
):
    # Validate GSTIN
    if not validate_gstin_checksum(payload.gstin):
        raise HTTPException(status_code=400, detail='Invalid GSTIN checksum')

    # Extract and verify PAN matches
    extracted_pan = extract_pan_from_gstin(payload.gstin)
    if extracted_pan != payload.pan:
        raise HTTPException(status_code=400, detail='PAN does not match GSTIN')

    # Call external APIs for prefill data
    gst_data = call_external_api('gst_details', {'gstin': payload.gstin})
    pan_data = call_external_api('pan_verification', {'pan': payload.pan})

    if not pan_data.get('valid'):
        raise HTTPException(status_code=400, detail='PAN verification failed')

    # Store in onboarding_jobs table
    db = SessionLocal()
    try:
        job_id = uuid4()
        prefilled_data = {
            'gstin': payload.gstin,
            'pan': encrypt_pan(payload.pan),
            'email': payload.email,
            'phone': payload.phone,
            'company_name': gst_data.get('company_name'),
            'trade_name': gst_data.get('trade_name'),
            'primary_state': gst_data.get('primary_state'),
            'gst_type': gst_data.get('gst_type'),
            'pan_holder_name': pan_data.get('name')
        }

        db.execute(text("""
            INSERT INTO onboarding_jobs (onboarding_job_id, company_id, job_type, status, input_data, output_data)
            VALUES (:job_id, :company_id, 'api_prefill', 'completed', :input, :output)
        """), {
            'job_id': job_id,
            'company_id': current_context.company_id,
            'input': {'gstin': payload.gstin, 'pan': payload.pan, 'email': payload.email, 'phone': payload.phone},
            'output': prefilled_data
        })
        db.commit()

        return APIOnboardingResponse(
            company_id=current_context.company_id,
            status='api_prefilled',
            prefilled_data=prefilled_data,
            requires_confirmation=True
        )
    finally:
        db.close()

@router.post('/onboarding/ocr-upload', response_model=OCRUploadResponse)
async def ocr_based_onboarding(
    document_type: str,
    file: UploadFile = File(...),
    current_context: TenantContext = Depends(get_current_context)
):
    # Validate document type
    valid_types = ['gst_certificate', 'pan_card', 'udyam_certificate', 'mca_certificate', 'bank_proof']
    if document_type not in valid_types:
        raise HTTPException(status_code=400, detail='Invalid document type')

    # Store file in object storage (mock - in production use S3, GCS, etc.)
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    document_url = f"s3://kyc-documents/{current_context.company_id}/{document_type}_{file_hash}.pdf"

    # Create KYC document record
    db = SessionLocal()
    try:
        kyc_doc_id = uuid4()
        db.execute(text("""
            INSERT INTO kyc_documents (kyc_document_id, company_id, document_type, document_url, status)
            VALUES (:id, :company_id, :doc_type, :url, 'pending')
        """), {
            'id': kyc_doc_id,
            'company_id': current_context.company_id,
            'doc_type': document_type,
            'url': document_url
        })

        # Create OCR job
        job_id = uuid4()
        db.execute(text("""
            INSERT INTO onboarding_jobs (onboarding_job_id, company_id, job_type, status, input_data)
            VALUES (:job_id, :company_id, 'ocr_extraction', 'pending', :input)
        """), {
            'job_id': job_id,
            'company_id': current_context.company_id,
            'input': {'kyc_document_id': str(kyc_doc_id), 'document_type': document_type, 'document_url': document_url}
        })
        db.commit()

        # Trigger async OCR processing (in production use message queue)
        # For now, simulate immediate processing
        await process_ocr_job(job_id, document_url, document_type, kyc_doc_id, current_context.company_id)

        return OCRUploadResponse(
            kyc_document_id=kyc_doc_id,
            job_id=job_id,
            status='processing'
        )
    finally:
        db.close()

async def process_ocr_job(job_id: UUID, document_url: str, document_type: str, kyc_doc_id: UUID, company_id: UUID):
    """Async OCR processing"""
    try:
        # Mock OCR processing
        if document_type == 'pan_card':
            extracted_data = {'pan': 'ABCDE1234F', 'name': 'John Doe', 'confidence': 0.95}
        elif document_type == 'gst_certificate':
            extracted_data = {'gstin': '22ABCDE1234F1Z5', 'company_name': 'Sample Company', 'confidence': 0.92}
        else:
            extracted_data = {'confidence': 0.88}

        confidence = extracted_data.get('confidence', 0.5)
        status = 'confirmed' if confidence >= 0.85 else 'pending'

        db = SessionLocal()
        try:
            # Update KYC document
            db.execute(text("""
                UPDATE kyc_documents
                SET extracted_data = :data, confidence = :conf, status = :status, ocr_metadata = :meta
                WHERE kyc_document_id = :id
            """), {
                'data': extracted_data,
                'conf': confidence,
                'status': status,
                'meta': {'ocr_engine': 'tesseract', 'processing_time': 2.5},
                'id': kyc_doc_id
            })

            # Update job
            db.execute(text("""
                UPDATE onboarding_jobs
                SET status = 'completed', output_data = :output, completed_at = now()
                WHERE onboarding_job_id = :job_id
            """), {
                'output': extracted_data,
                'job_id': job_id
            })
            db.commit()
        finally:
            db.close()

    except Exception as e:
        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE onboarding_jobs
                SET status = 'failed', error_message = :error, completed_at = now()
                WHERE onboarding_job_id = :job_id
            """), {
                'error': str(e),
                'job_id': job_id
            })
            db.commit()
        finally:
            db.close()

@router.get('/onboarding/job/{job_id}', response_model=OnboardingJobStatus)
async def get_job_status(
    job_id: UUID,
    current_context: TenantContext = Depends(get_current_context)
):
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT status, output_data, error_message
            FROM onboarding_jobs
            WHERE onboarding_job_id = :job_id AND company_id = :company_id
        """), {'job_id': job_id, 'company_id': current_context.company_id}).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail='Job not found')

        return OnboardingJobStatus(
            job_id=job_id,
            status=result.status,
            extracted_data=result.output_data,
            confidence=result.output_data.get('confidence') if result.output_data else None,
            error_message=result.error_message
        )
    finally:
        db.close()

@router.post('/onboarding/confirm', response_model=OnboardingConfirmationResponse)
async def confirm_onboarding(
    payload: OnboardingConfirmationRequest,
    current_context: TenantContext = Depends(get_current_context)
):
    # Validate that all required documents are confirmed
    db = SessionLocal()
    try:
        # Check KYC documents
        kyc_docs = db.execute(text("""
            SELECT document_type, status, extracted_data
            FROM kyc_documents
            WHERE kyc_document_id = ANY(:ids) AND company_id = :company_id
        """), {
            'ids': payload.kyc_document_ids,
            'company_id': current_context.company_id
        }).fetchall()

        required_docs = {'pan_card', 'gst_certificate'}
        provided_docs = {doc.document_type for doc in kyc_docs}

        if not required_docs.issubset(provided_docs):
            raise HTTPException(status_code=400, detail='Missing required documents')

        # Check if all docs are confirmed
        unconfirmed = [doc for doc in kyc_docs if doc.status != 'confirmed']
        if unconfirmed:
            raise HTTPException(status_code=400, detail='All documents must be confirmed before onboarding')

        # Extract company data
        company_data = payload.company_data
        pan = company_data.get('pan')
        gstin = company_data.get('gstin')

        # Validate data consistency
        for doc in kyc_docs:
            if doc.document_type == 'pan_card' and doc.extracted_data:
                extracted_pan = doc.extracted_data.get('pan')
                if extracted_pan and extracted_pan != pan:
                    raise HTTPException(status_code=400, detail='PAN mismatch between documents')
            elif doc.document_type == 'gst_certificate' and doc.extracted_data:
                extracted_gstin = doc.extracted_data.get('gstin')
                if extracted_gstin and extracted_gstin != gstin:
                    raise HTTPException(status_code=400, detail='GSTIN mismatch between documents')

        # Create or update company
        company_id = payload.company_data.get('company_id', current_context.company_id)

        # Encrypt PAN
        if not pan:
            raise HTTPException(status_code=400, detail='PAN is required')
        encrypted_pan = encrypt_pan(pan)

        db.execute(text("""
            INSERT INTO companies (
                company_id, company_name, trade_name, company_type, pan, gstin,
                gst_type, primary_state, onboarding_completed
            ) VALUES (
                :id, :name, :trade_name, :type, :pan, :gstin,
                :gst_type, :state, TRUE
            )
            ON CONFLICT (company_id) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                trade_name = EXCLUDED.trade_name,
                pan = EXCLUDED.pan,
                gstin = EXCLUDED.gstin,
                onboarding_completed = TRUE,
                updated_at = now()
        """), {
            'id': company_id,
            'name': company_data['company_name'],
            'trade_name': company_data.get('trade_name'),
            'type': company_data.get('company_type', 'pvt_ltd'),
            'pan': encrypted_pan,
            'gstin': gstin,
            'gst_type': company_data.get('gst_type', 'regular'),
            'state': company_data['primary_state']
        })

        # Create default roles and owner user
        owner_email = company_data.get('email')
        owner_name = company_data.get('pan_holder_name', 'Owner')
        if owner_email:
            create_default_roles_and_user(db, company_id, owner_email, owner_name)

        # Update KYC documents as confirmed
        db.execute(text("""
            UPDATE kyc_documents
            SET confirmed_at = now(), confirmed_by = :user_id
            WHERE kyc_document_id = ANY(:ids)
        """), {
            'user_id': current_context.user_id,
            'ids': payload.kyc_document_ids
        })

        db.commit()

        return OnboardingConfirmationResponse(
            company_id=company_id,
            onboarding_completed=True
        )
    finally:
        db.close()

@router.get('/onboarding/status')
async def get_onboarding_status(current_context: TenantContext = Depends(get_current_context)):
    db = SessionLocal()
    try:
        company = db.execute(text("""
            SELECT onboarding_completed FROM companies WHERE company_id = :company_id
        """), {'company_id': current_context.company_id}).fetchone()

        kyc_docs = db.execute(text("""
            SELECT document_type, status, confidence FROM kyc_documents
            WHERE company_id = :company_id
        """), {'company_id': current_context.company_id}).fetchall()

        jobs = db.execute(text("""
            SELECT job_type, status FROM onboarding_jobs
            WHERE company_id = :company_id
        """), {'company_id': current_context.company_id}).fetchall()

        return {
            'company_id': current_context.company_id,
            'onboarding_completed': company.onboarding_completed if company else False,
            'kyc_documents': [{'type': doc.document_type, 'status': doc.status, 'confidence': doc.confidence} for doc in kyc_docs],
            'jobs': [{'type': job.job_type, 'status': job.status} for job in jobs]
        }
    finally:
        db.close()

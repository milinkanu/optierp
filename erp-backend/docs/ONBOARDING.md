# Onboarding Module Documentation

## Overview

The Onboarding Module provides two methods for company registration in the FinOps system:

1. **API-based Onboarding**: Prefill company data using GSTIN, PAN, email, and phone via external API calls
2. **OCR-based Onboarding**: Upload KYC documents for automated data extraction

Both methods require user confirmation before finalizing the company record.

## Architecture

### Database Schema

#### New Tables Added

```sql
-- Added to companies table
onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE

-- KYC Documents table
CREATE TABLE kyc_documents (
    kyc_document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    document_type kyc_document_type_enum NOT NULL,
    document_url TEXT NOT NULL, -- Object storage URL
    extracted_data JSONB,
    ocr_metadata JSONB,
    confidence NUMERIC(5,4) CHECK (confidence >= 0 AND confidence <= 1),
    status ocr_status_enum NOT NULL DEFAULT 'pending',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at TIMESTAMPTZ,
    confirmed_by UUID REFERENCES users(user_id)
);

-- Onboarding Jobs table
CREATE TABLE onboarding_jobs (
    onboarding_job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    job_type TEXT NOT NULL, -- 'api_prefill' or 'ocr_extraction'
    status onboarding_job_status_enum NOT NULL DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

#### New Enums

```sql
CREATE TYPE kyc_document_type_enum AS ENUM ('gst_certificate','pan_card','udyam_certificate','mca_certificate','bank_proof');
CREATE TYPE onboarding_status_enum AS ENUM ('draft','api_prefilled','ocr_pending','ocr_completed','confirmed','completed','failed');
CREATE TYPE onboarding_job_status_enum AS ENUM ('pending','processing','completed','failed');
```

#### Constraints

- **PAN Format**: `^[A-Z]{5}[0-9]{4}[A-Z]{1}$`
- **GSTIN Format**: `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`
- **Phone Format**: `^\+91[6-9]\d{9}$`
- **GSTIN Checksum**: Validates using standard GST algorithm

## API Endpoints

### 1. API-based Onboarding

**POST** `/onboarding/api-prefill`

**Request Body:**
```json
{
  "gstin": "22ABCDE1234F1Z5",
  "pan": "ABCDE1234F",
  "email": "contact@company.com",
  "phone": "+919876543210"
}
```

**Response:**
```json
{
  "company_id": "uuid",
  "status": "api_prefilled",
  "prefilled_data": {
    "gstin": "22ABCDE1234F1Z5",
    "pan": "encrypted_pan",
    "email": "contact@company.com",
    "phone": "+919876543210",
    "company_name": "Sample Company Pvt Ltd",
    "trade_name": "Sample Trade",
    "primary_state": "Maharashtra",
    "gst_type": "regular",
    "pan_holder_name": "John Doe"
  },
  "requires_confirmation": true
}
```

**Validation Rules:**
- GSTIN checksum validation
- PAN extraction from GSTIN and comparison
- External API calls for GST details and PAN verification

### 2. OCR-based Document Upload

**POST** `/onboarding/ocr-upload`

**Form Data:**
- `document_type`: gst_certificate | pan_card | udyam_certificate | mca_certificate | bank_proof
- `file`: PDF/image file

**Response:**
```json
{
  "kyc_document_id": "uuid",
  "job_id": "uuid",
  "status": "processing"
}
```

### 3. Check Job Status

**GET** `/onboarding/job/{job_id}`

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "extracted_data": {
    "pan": "ABCDE1234F",
    "name": "John Doe",
    "confidence": 0.95
  },
  "confidence": 0.95,
  "error_message": null
}
```

### 4. Confirm Onboarding

**POST** `/onboarding/confirm`

**Request Body:**
```json
{
  "company_data": {
    "company_name": "Sample Company Pvt Ltd",
    "trade_name": "Sample Trade",
    "company_type": "pvt_ltd",
    "pan": "ABCDE1234F",
    "gstin": "22ABCDE1234F1Z5",
    "gst_type": "regular",
    "primary_state": "Maharashtra"
  },
  "kyc_document_ids": ["uuid1", "uuid2"]
}
```

**Response:**
```json
{
  "company_id": "uuid",
  "onboarding_completed": true
}
```

### 5. Get Onboarding Status

**GET** `/onboarding/status`

**Response:**
```json
{
  "company_id": "uuid",
  "onboarding_completed": false,
  "kyc_documents": [
    {
      "type": "pan_card",
      "status": "confirmed",
      "confidence": 0.95
    }
  ],
  "jobs": [
    {
      "type": "ocr_extraction",
      "status": "completed"
    }
  ]
}
```

## Transaction Flow

### API-based Flow

1. **Input Validation**
   - Validate GSTIN format and checksum
   - Extract PAN from GSTIN and compare with provided PAN
   - Validate email and phone formats

2. **External API Calls**
   - GST API for company details
   - PAN verification API
   - Store results in `onboarding_jobs` table

3. **User Confirmation**
   - Return prefilled data for user review
   - User calls `/onboarding/confirm` with final data

4. **Company Creation**
   - Encrypt PAN using AES-256
   - Create/update company record
   - Set `onboarding_completed = TRUE`

### OCR-based Flow

1. **Document Upload**
   - Validate document type
   - Store file in object storage
   - Create `kyc_documents` record
   - Create `onboarding_jobs` record

2. **Async OCR Processing**
   - Trigger OCR job (message queue in production)
   - Extract data with confidence scores
   - Update records when complete

3. **User Review**
   - If confidence >= 0.85, mark as 'confirmed'
   - If confidence < 0.85, require manual confirmation

4. **Final Confirmation**
   - Validate all required documents present
   - Check data consistency across documents
   - Create company record

## Validation Rules

### GSTIN Validation
- **Format**: 15 characters: `22ABCDE1234F1Z5`
- **Checksum**: Uses weighted sum algorithm
- **PAN Extraction**: Characters 2-11 form the PAN

### PAN Validation
- **Format**: 10 characters: `AAAAA1111A`
- **Encryption**: AES-256 with Fernet
- **Storage**: Always encrypted in database

### Document Requirements
- **Required**: PAN card, GST certificate
- **Optional**: Udyam certificate, MCA certificate, Bank proof
- **Confidence Threshold**: 0.85 for auto-confirmation

### Data Consistency
- PAN from GSTIN must match provided PAN
- Company name across documents must be consistent
- GSTIN across documents must match

## Failure Handling

### API Failures
- **GST API Failure**: Return error, allow manual entry
- **PAN API Failure**: Return error, require manual verification
- **Network Issues**: Retry logic with exponential backoff

### OCR Failures
- **Low Confidence**: Mark as 'pending', require manual confirmation
- **Processing Errors**: Update job status to 'failed' with error message
- **Document Corruption**: Reject upload with error

### Validation Failures
- **Format Errors**: Return 400 with specific error message
- **Consistency Errors**: Return 400 with mismatch details
- **Missing Documents**: Return 400 with requirements list

## Security Measures

- **PAN Encryption**: AES-256 encryption at rest
- **Tenant Isolation**: RLS policies enforce company_id isolation
- **JWT Authentication**: All endpoints require valid JWT token
- **RBAC**: User roles control access to onboarding operations
- **Audit Logging**: All operations logged with tamper-evident hashing

## Performance Considerations

- **Async Processing**: OCR jobs processed asynchronously
- **Object Storage**: Documents stored externally, URLs in database
- **Indexing**: Composite indexes on company_id + timestamps
- **Connection Pooling**: SQLAlchemy connection pooling for DB access

## Edge Cases

1. **GSTIN with Special Characters**: Handle Z and numeric check digits
2. **Multiple PAN Holders**: Support different PAN for company vs. directors
3. **State Code Changes**: Handle GST state code updates
4. **Document Re-uploads**: Allow replacing documents before confirmation
5. **Partial Onboarding**: Support resuming incomplete onboarding
6. **Duplicate Companies**: Prevent duplicate GSTIN/PAN combinations
7. **Expired Documents**: Add expiry date validation for certificates
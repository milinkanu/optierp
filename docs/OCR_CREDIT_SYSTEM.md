# OCR and Credit System Design

## System Architecture

### Components
- **Document Upload Service**: Handles file uploads and storage
- **OCR Processing Engine**: PaddleOCR primary, VLM fallback
- **Credit Management**: Tenant credit balance and ledger
- **Result Confirmation**: Manual review and confirmation

### Processing Pipeline

1. **Document Upload**
   - User uploads document via `/documents/upload`
   - File stored in object storage
   - Document record created in `documents` table
   - If mode != manual, trigger async OCR processing

2. **OCR Processing**
   - For OCR/Smart mode: Run PaddleOCR
   - If confidence < 0.85 and Smart mode:
     - Check credit balance
     - If insufficient credits: Fail with error
     - Else: Deduct 1 credit, run VLM
   - Store results in `ocr_results` table
   - Status: confirmed if high confidence, pending if low, failed if error

3. **Result Handling**
   - High confidence: Auto-confirm
   - Low confidence: Require manual confirmation
   - Failed: Show error message

4. **Credit Management**
   - Subscription: Periodic credit addition
   - Pay-as-you-go: Credits purchased on-demand
   - Deduction: 1 credit per VLM call

## PostgreSQL Schema

### Tables Added

#### documents
- Stores uploaded document metadata
- Links to object storage URL

#### ocr_results
- Stores OCR processing results
- JSONB for extracted_data
- Tracks PaddleOCR and VLM confidence

#### credit_ledger
- Immutable ledger of credit transactions
- Tracks balance changes

#### companies (extended)
- Added credit_balance column

## APIs

### Document Management
- `POST /documents/upload` - Upload document
- `GET /documents/{id}` - Get document info

### OCR Processing
- `POST /ocr/process` - Manual OCR trigger
- `PATCH /ocr/{id}/confirm` - Confirm OCR result
- `GET /ocr/results/{document_id}` - Get OCR results

### Credit Management
- `GET /credits/balance` - Get current balance
- `POST /credits/add` - Add credits (admin)
- `GET /credits/ledger` - Get credit transaction history

## Failure Handling

### Low Confidence
- Status set to 'pending'
- User notified to review and confirm manually

### Insufficient Credits
- VLM processing skipped
- Error returned: "Insufficient credits"
- User prompted to purchase credits

### OCR Engine Failure
- Status set to 'failed'
- Retry logic or manual processing

### Validation Rules
- Credit deduction only on successful VLM call
- All financial data validated before storage
- Audit logs for all credit transactions

## Modes

### Manual
- No OCR processing
- User enters data manually

### OCR
- Only PaddleOCR
- If confidence < 0.85, mark as pending

### Smart
- PaddleOCR first
- VLM fallback if needed and credits available

## Security
- Tenant isolation via RLS
- JWT authentication
- Credit balance checks before expensive operations
- Audit logging for all changes</content>
<parameter name="filePath">c:\Users\Milin\Desktop\OptiReach\optierp4\OCR_CREDIT_SYSTEM.md
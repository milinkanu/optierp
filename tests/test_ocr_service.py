"""
Integration tests for ocr_service.py endpoints
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime

from services.ocr_service import app, DocumentType, OCRMode


class TestOCRService:
    """Test OCR service endpoints"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    @pytest.fixture
    def valid_headers(self):
        """Create valid headers for requests"""
        from services.common import create_access_token
        
        company_id = uuid4()
        user_id = uuid4()
        token = create_access_token(
            subject=str(user_id),
            company_id=company_id,
            user_version=1,
            roles=['owner'],
            delegations=[]
        )
        
        return {
            'Authorization': f'Bearer {token}',
            'X-Tenant-ID': str(company_id),
            'X-User-ID': str(user_id),
            'X-User-Roles': 'owner'
        }

    def test_document_type_enum_values(self):
        """Test DocumentType enum values"""
        assert DocumentType.INVOICE == 'invoice'
        assert DocumentType.RECEIPT == 'receipt'
        assert DocumentType.BANK_STATEMENT == 'bank_statement'
        assert DocumentType.KYC == 'kyc'
        assert DocumentType.OTHER == 'other'

    def test_ocr_mode_enum_values(self):
        """Test OCRMode enum values"""
        assert OCRMode.MANUAL == 'manual'
        assert OCRMode.OCR == 'ocr'
        assert OCRMode.SMART == 'smart'

    def test_document_upload_request_model(self):
        """Test DocumentUploadRequest model"""
        from services.ocr_service import DocumentUploadRequest
        
        request = DocumentUploadRequest(
            document_type=DocumentType.INVOICE,
            mode=OCRMode.OCR
        )
        
        assert request.document_type == 'invoice'
        assert request.mode == 'ocr'

    def test_document_response_model(self):
        """Test DocumentResponse model"""
        from services.ocr_service import DocumentResponse
        
        company_id = uuid4()
        document_id = uuid4()
        
        response = DocumentResponse(
            document_id=document_id,
            company_id=company_id,
            document_type=DocumentType.INVOICE,
            file_name='invoice.pdf',
            file_url='/documents/invoice.pdf',
            uploaded_at=datetime.utcnow()
        )
        
        assert response.document_id == document_id
        assert response.file_name == 'invoice.pdf'

    def test_ocr_process_request_model(self):
        """Test OCRProcessRequest model"""
        from services.ocr_service import OCRProcessRequest
        
        document_id = uuid4()
        request = OCRProcessRequest(
            document_id=document_id,
            mode=OCRMode.SMART
        )
        
        assert request.document_id == document_id
        assert request.mode == 'smart'

    def test_ocr_result_response_model(self):
        """Test OCRResultResponse model"""
        from services.ocr_service import OCRResultResponse
        
        ocr_result_id = uuid4()
        document_id = uuid4()
        company_id = uuid4()
        
        extracted_data = {
            'invoice_number': 'INV-001',
            'total_amount': 1000.0,
            'vendor_name': 'Test Vendor'
        }
        
        response = OCRResultResponse(
            ocr_result_id=ocr_result_id,
            document_id=document_id,
            company_id=company_id,
            mode=OCRMode.OCR,
            paddleocr_confidence=0.92,
            vlm_confidence=0.95,
            extracted_data=extracted_data,
            status='completed',
            processed_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        
        assert response.status == 'completed'
        assert response.paddleocr_confidence == 0.92
        assert response.extracted_data['invoice_number'] == 'INV-001'

    def test_credit_balance_response_model(self):
        """Test CreditBalanceResponse model"""
        from services.ocr_service import CreditBalanceResponse
        
        company_id = uuid4()
        response = CreditBalanceResponse(
            company_id=company_id,
            credit_balance=100.0
        )
        
        assert response.company_id == company_id
        assert response.credit_balance == 100.0

    def test_confirm_ocr_request_model(self):
        """Test ConfirmOCRRequest model"""
        from services.ocr_service import ConfirmOCRRequest
        
        ocr_result_id = uuid4()
        extracted_data = {
            'vendor_name': 'Test Vendor',
            'invoice_amount': 5000.0
        }
        
        request = ConfirmOCRRequest(
            ocr_result_id=ocr_result_id,
            extracted_data=extracted_data
        )
        
        assert request.ocr_result_id == ocr_result_id
        assert request.extracted_data['vendor_name'] == 'Test Vendor'

    def test_ocr_result_with_partial_confidence(self):
        """Test OCR result where only one confidence is provided"""
        from services.ocr_service import OCRResultResponse
        
        response = OCRResultResponse(
            ocr_result_id=uuid4(),
            document_id=uuid4(),
            company_id=uuid4(),
            mode=OCRMode.OCR,
            paddleocr_confidence=0.85,
            vlm_confidence=None,  # Optional
            extracted_data={'key': 'value'},
            status='completed',
            created_at=datetime.utcnow()
        )
        
        assert response.paddleocr_confidence == 0.85
        assert response.vlm_confidence is None

    def test_ocr_result_failed_status(self):
        """Test OCR result with failed status"""
        from services.ocr_service import OCRResultResponse
        
        response = OCRResultResponse(
            ocr_result_id=uuid4(),
            document_id=uuid4(),
            company_id=uuid4(),
            mode=OCRMode.MANUAL,
            extracted_data={},
            status='failed',
            created_at=datetime.utcnow(),
            error_message='File too large'
        )
        
        assert response.status == 'failed'
        assert response.error_message == 'File too large'

    def test_credit_balance_endpoint(self, client, valid_headers):
        """Test credit balance endpoint does not require configured DB"""
        response = client.get('/credits/balance', headers=valid_headers)

        assert response.status_code == 200
        data = response.json()
        assert data['credit_balance'] == 100.0

    def test_upload_process_and_confirm_manual_document(self, client, valid_headers):
        """Test manual document upload, OCR processing, and confirmation flow"""
        upload_response = client.post(
            '/documents/upload',
            params={'document_type': 'invoice', 'mode': 'manual'},
            files={'file': ('invoice.txt', b'invoice text', 'text/plain')},
            headers=valid_headers
        )

        assert upload_response.status_code == 200
        document_id = upload_response.json()['document_id']

        process_response = client.post(
            '/ocr/process',
            json={'document_id': document_id, 'mode': 'manual'},
            headers=valid_headers
        )

        assert process_response.status_code == 200
        ocr_result = process_response.json()
        assert ocr_result['document_id'] == document_id
        assert ocr_result['status'] == 'pending'

        confirm_response = client.patch(
            f"/ocr/{ocr_result['ocr_result_id']}/confirm",
            json={
                'ocr_result_id': ocr_result['ocr_result_id'],
                'extracted_data': {'invoice_number': 'INV-001'}
            },
            headers=valid_headers
        )

        assert confirm_response.status_code == 200
        assert confirm_response.json()['status'] == 'confirmed'

    def test_process_unknown_document_returns_404(self, client, valid_headers):
        """Test OCR process returns a clear error for unknown documents"""
        response = client.post(
            '/ocr/process',
            json={'document_id': str(uuid4()), 'mode': 'manual'},
            headers=valid_headers
        )

        assert response.status_code == 404

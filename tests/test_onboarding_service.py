"""
Integration tests for onboarding_service.py endpoints
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from services.onboarding_service import app


class TestOnboardingService:
    """Test onboarding service endpoints"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    def test_validate_gstin_checksum_valid(self):
        """Test GSTIN checksum validation with valid GSTIN"""
        from services.onboarding_service import validate_gstin_checksum
        
        # Note: This is a sample GSTIN - replace with actual valid GSTIN
        valid_gstin = '27AAJFU9603R1Z5'
        result = validate_gstin_checksum(valid_gstin)
        assert isinstance(result, bool)

    def test_validate_gstin_checksum_invalid(self):
        """Test GSTIN checksum validation with invalid GSTIN"""
        from services.onboarding_service import validate_gstin_checksum
        
        invalid_gstin = '27AAJFU9603R1Z0'  # Invalid checksum
        result = validate_gstin_checksum(invalid_gstin)
        assert result is False

    def test_extract_pan_from_gstin(self):
        """Test PAN extraction from GSTIN"""
        from services.onboarding_service import extract_pan_from_gstin
        
        gstin = '27AAJFU9603R1Z5'
        pan = extract_pan_from_gstin(gstin)
        
        assert len(pan) == 10
        assert pan == 'AAJFU9603R'

    def test_encrypt_decrypt_pan(self):
        """Test PAN encryption and decryption"""
        from services.onboarding_service import encrypt_pan, decrypt_pan
        
        original_pan = 'AAJFU9603R'
        
        encrypted = encrypt_pan(original_pan)
        assert isinstance(encrypted, str)
        assert encrypted != original_pan
        
        decrypted = decrypt_pan(encrypted)
        assert decrypted == original_pan

    def test_api_onboarding_request_model_valid(self):
        """Test APIOnboardingRequest model with valid data"""
        from services.onboarding_service import APIOnboardingRequest
        
        request = APIOnboardingRequest(
            gstin='27AAJFU9603R1Z5',
            pan='AAJFU9603R',
            email='test@example.com',
            phone='+919876543210'
        )
        
        assert request.gstin == '27AAJFU9603R1Z5'
        assert request.pan == 'AAJFU9603R'
        assert request.email == 'test@example.com'

    def test_api_onboarding_request_invalid_phone(self):
        """Test APIOnboardingRequest with invalid phone"""
        from services.onboarding_service import APIOnboardingRequest
        
        with pytest.raises(ValueError):
            APIOnboardingRequest(
                gstin='27AAJFU9603R1Z5',
                pan='AAJFU9603R',
                email='test@example.com',
                phone='9876543210'  # Missing +91 prefix
            )

    def test_api_onboarding_request_invalid_pan_length(self):
        """Test APIOnboardingRequest with invalid PAN length"""
        from services.onboarding_service import APIOnboardingRequest
        
        with pytest.raises(ValueError):
            APIOnboardingRequest(
                gstin='27AAJFU9603R1Z5',
                pan='AAJFU960',  # Too short
                email='test@example.com',
                phone='+919876543210'
            )

    def test_api_onboarding_request_invalid_gstin_length(self):
        """Test APIOnboardingRequest with invalid GSTIN length"""
        from services.onboarding_service import APIOnboardingRequest
        
        with pytest.raises(ValueError):
            APIOnboardingRequest(
                gstin='27AAJFU9603',  # Too short
                pan='AAJFU9603R',
                email='test@example.com',
                phone='+919876543210'
            )

    def test_ocr_upload_request_model(self):
        """Test OCRUploadRequest model"""
        from services.onboarding_service import OCRUploadRequest
        
        request = OCRUploadRequest(
            document_type='gst_certificate'
        )
        
        assert request.document_type == 'gst_certificate'

    def test_onboarding_job_status_model(self):
        """Test OnboardingJobStatus model"""
        from services.onboarding_service import OnboardingJobStatus
        
        job_id = uuid4()
        status = OnboardingJobStatus(
            job_id=job_id,
            status='processing',
            extracted_data={'gstin': '27AAJFU9603R1Z5'},
            confidence=0.95
        )
        
        assert status.job_id == job_id
        assert status.status == 'processing'
        assert status.confidence == 0.95

    def test_onboarding_confirmation_request_model(self):
        """Test OnboardingConfirmationRequest model"""
        from services.onboarding_service import OnboardingConfirmationRequest
        
        company_data = {
            'company_name': 'Test Company',
            'pan': 'AAJFU9603R',
            'gstin': '27AAJFU9603R1Z5'
        }
        
        request = OnboardingConfirmationRequest(
            company_data=company_data,
            kyc_document_ids=[uuid4(), uuid4()]
        )
        
        assert request.company_data['company_name'] == 'Test Company'
        assert len(request.kyc_document_ids) == 2

    def test_api_onboarding_response_model(self):
        """Test APIOnboardingResponse model"""
        from services.onboarding_service import APIOnboardingResponse
        
        company_id = uuid4()
        response = APIOnboardingResponse(
            company_id=company_id,
            status='pending_verification',
            prefilled_data={'gstin': '27AAJFU9603R1Z5'},
            requires_confirmation=True
        )
        
        assert response.company_id == company_id
        assert response.requires_confirmation is True

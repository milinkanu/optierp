"""
Integration tests for compliance_service.py endpoints
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import date

from services.compliance_service import app


class TestComplianceService:
    """Test compliance service endpoints"""

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

    def test_tax_rate_config_model_gst(self):
        """Test TaxRateConfig model for GST"""
        from services.compliance_service import TaxRateConfig
        
        config = TaxRateConfig(
            tax_type='gst',
            section_code='GST_001',
            rate=18.0,
            effective_from=date.today()
        )
        
        assert config.tax_type == 'gst'
        assert config.rate == 18.0

    def test_tax_rate_config_model_tds(self):
        """Test TaxRateConfig model for TDS"""
        from services.compliance_service import TaxRateConfig
        
        config = TaxRateConfig(
            tax_type='tds',
            section_code='194C',
            rate=10.0,
            effective_from=date.today()
        )
        
        assert config.tax_type == 'tds'
        assert config.section_code == '194C'

    def test_tax_rate_config_invalid_type(self):
        """Test TaxRateConfig with invalid type"""
        from services.compliance_service import TaxRateConfig
        
        with pytest.raises(ValueError):
            TaxRateConfig(
                tax_type='invalid_tax',
                rate=10.0,
                effective_from=date.today()
            )

    def test_tax_rate_config_rate_validation(self):
        """Test TaxRateConfig rate validation"""
        from services.compliance_service import TaxRateConfig
        
        # Valid rate
        config = TaxRateConfig(
            tax_type='gst',
            rate=18.0,
            effective_from=date.today()
        )
        assert config.rate == 18.0
        
        # Invalid rate (negative)
        with pytest.raises(ValueError):
            TaxRateConfig(
                tax_type='gst',
                rate=-5.0,
                effective_from=date.today()
            )
        
        # Invalid rate (> 100)
        with pytest.raises(ValueError):
            TaxRateConfig(
                tax_type='gst',
                rate=150.0,
                effective_from=date.today()
            )

    def test_tax_rule_config_model(self):
        """Test TaxRuleConfig model"""
        from services.compliance_service import TaxRuleConfig
        
        condition = {'amount': {'$gt': 50000}}
        action = {'rate': 28.0}
        
        config = TaxRuleConfig(
            rule_name='High Value Sale',
            tax_type='gst',
            condition_json=condition,
            action_json=action,
            priority=1
        )
        
        assert config.rule_name == 'High Value Sale'
        assert config.priority == 1

    def test_gst_liability_model(self):
        """Test GSTLiability model"""
        from services.compliance_service import GSTLiability
        
        gst_liability_id = uuid4()
        transaction_id = uuid4()
        
        liability = GSTLiability(
            gst_liability_id=gst_liability_id,
            transaction_id=transaction_id,
            gstin='27AAJFU9603R1Z5',
            component='sgst',
            taxable_amount=1000.0,
            rate=9.0,
            amount=90.0,
            period='2026-03',
            is_input=False
        )
        
        assert liability.component == 'sgst'
        assert liability.amount == 90.0

    def test_gst_liability_component_validation(self):
        """Test GSTLiability component validation"""
        from services.compliance_service import GSTLiability
        
        with pytest.raises(ValueError):
            GSTLiability(
                gst_liability_id=uuid4(),
                transaction_id=uuid4(),
                gstin='27AAJFU9603R1Z5',
                component='invalid_component',  # Invalid
                taxable_amount=1000.0,
                rate=9.0,
                amount=90.0,
                period='2026-03'
            )

    def test_gst_return_request_model(self):
        """Test GSTReturnRequest model"""
        from services.compliance_service import GSTReturnRequest
        
        request = GSTReturnRequest(
            return_type='GSTR3B',
            period='2026-03'
        )
        
        assert request.return_type == 'GSTR3B'
        assert request.period == '2026-03'

    def test_gst_return_response_model(self):
        """Test GSTReturnResponse model"""
        from services.compliance_service import GSTReturnResponse
        
        gst_return_id = uuid4()
        response = GSTReturnResponse(
            gst_return_id=gst_return_id,
            return_type='GSTR1',
            period='2026-03',
            status='draft',
            total_taxable_value=100000.0,
            total_tax_amount=18000.0,
            due_date=date(2026, 4, 20)
        )
        
        assert response.return_type == 'GSTR1'
        assert response.status == 'draft'

    def test_tds_deduction_model(self):
        """Test TDSDeduction model"""
        from services.compliance_service import TDSDeduction
        
        tds_id = uuid4()
        transaction_id = uuid4()
        
        tds = TDSDeduction(
            tds_deduction_id=tds_id,
            transaction_id=transaction_id,
            section='194C',
            deductee_name='ABC Contractors',
            deductee_pan='AAJFU9603R',
            payment_amount=100000.0,
            tds_rate=10.0,
            tds_amount=10000.0,
            period='2026-Q1'
        )
        
        assert tds.section == '194C'
        assert tds.tds_amount == 10000.0

    def test_tds_return_request_model(self):
        """Test TDSReturnRequest model"""
        from services.compliance_service import TDSReturnRequest
        
        request = TDSReturnRequest(
            form_no='24Q',
            period='2026-Q1'
        )
        
        assert request.form_no == '24Q'
        assert request.period == '2026-Q1'

    def test_tcs_collection_model(self):
        """Test TCSCollection model"""
        from services.compliance_service import TCSCollection
        
        tcs_id = uuid4()
        transaction_id = uuid4()
        
        tcs = TCSCollection(
            tcs_collection_id=tcs_id,
            transaction_id=transaction_id,
            section='206C',
            collectee_name='Test Collectee',
            collectee_pan='AAJFU9603R',
            receipt_amount=50000.0,
            tcs_rate=1.0,
            tcs_amount=500.0
        )
        
        assert tcs.section == '206C'
        assert tcs.tcs_rate == 1.0

    def test_gst_return_period_format(self):
        """Test GSTReturnRequest period format validation"""
        from services.compliance_service import GSTReturnRequest
        
        # Valid period
        request = GSTReturnRequest(
            return_type='GSTR3B',
            period='2026-03'
        )
        assert request.period == '2026-03'
        
        # Invalid period format
        with pytest.raises(ValueError):
            GSTReturnRequest(
                return_type='GSTR3B',
                period='2026/03'  # Wrong format
            )

    def test_tds_return_quarter_format(self):
        """Test TDSReturnRequest quarter format validation"""
        from services.compliance_service import TDSReturnRequest
        
        # Valid quarter
        request = TDSReturnRequest(
            form_no='24Q',
            period='2026-Q1'
        )
        assert request.period == '2026-Q1'
        
        # Invalid quarter
        with pytest.raises(ValueError):
            TDSReturnRequest(
                form_no='24Q',
                period='2026-Q5'  # Invalid quarter
            )

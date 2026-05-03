"""
Integration tests for invoice_service.py endpoints
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import date, timedelta
from decimal import Decimal

from services.invoice_service import app


class TestInvoiceService:
    """Test invoice service endpoints"""

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

    def test_create_sales_invoice_valid(self, client, valid_headers):
        """Test creating a valid sales invoice"""
        account_id = uuid4()
        billing_party_id = uuid4()

        payload = {
            'invoice_type': 'sales_invoice',
            'invoice_date': str(date.today()),
            'due_date': str(date.today() + timedelta(days=30)),
            'billing_party_id': str(billing_party_id),
            'currency': 'INR',
            'exchange_rate': 1.0,
            'items': [
                {
                    'description': 'Product A',
                    'hsn_sac': '421000',
                    'account_id': str(account_id),
                    'quantity': 5.0,
                    'unit_price': 100.00,
                    'discount_amount': 10.00,
                    'gst_rate': 18.00
                }
            ]
        }

        response = client.post(
            '/invoices',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'invoice_id' in data
        assert 'invoice_number' in data
        assert data['invoice_type'] == 'sales_invoice'

    def test_create_purchase_invoice_valid(self, client, valid_headers):
        """Test creating a valid purchase invoice"""
        account_id = uuid4()
        billing_party_id = uuid4()

        payload = {
            'invoice_type': 'purchase_invoice',
            'invoice_date': str(date.today()),
            'billing_party_id': str(billing_party_id),
            'items': [
                {
                    'description': 'Raw Material',
                    'hsn_sac': '701090',
                    'account_id': str(account_id),
                    'quantity': 10.0,
                    'unit_price': 50.00,
                    'gst_rate': 5.00
                }
            ]
        }

        response = client.post(
            '/invoices',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data['invoice_type'] == 'purchase_invoice'

    def test_create_invoice_invalid_type(self, client, valid_headers):
        """Test creating invoice with invalid type"""
        payload = {
            'invoice_type': 'invalid_type',
            'invoice_date': str(date.today()),
            'billing_party_id': str(uuid4()),
            'items': [
                {
                    'description': 'Item',
                    'hsn_sac': '421000',
                    'account_id': str(uuid4()),
                    'quantity': 1.0,
                    'unit_price': 100.00,
                    'gst_rate': 18.00
                }
            ]
        }

        response = client.post(
            '/invoices',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 400

    def test_create_invoice_no_line_items(self, client, valid_headers):
        """Test creating invoice without line items"""
        payload = {
            'invoice_type': 'sales_invoice',
            'invoice_date': str(date.today()),
            'billing_party_id': str(uuid4()),
            'items': []
        }

        response = client.post(
            '/invoices',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 400

    def test_create_invoice_with_tds_tcs(self, client, valid_headers):
        """Test creating invoice with TDS and TCS rates"""
        account_id = uuid4()
        billing_party_id = uuid4()

        payload = {
            'invoice_type': 'sales_invoice',
            'invoice_date': str(date.today()),
            'billing_party_id': str(billing_party_id),
            'items': [
                {
                    'description': 'Service',
                    'hsn_sac': '999829',
                    'account_id': str(account_id),
                    'quantity': 1.0,
                    'unit_price': 10000.00,
                    'gst_rate': 18.00,
                    'tds_rate': 10.00,
                    'tcs_rate': 0.0
                }
            ]
        }

        response = client.post(
            '/invoices',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200

    def test_create_invoice_multiple_items(self, client, valid_headers):
        """Test creating invoice with multiple items"""
        account_id_1 = uuid4()
        account_id_2 = uuid4()
        billing_party_id = uuid4()

        payload = {
            'invoice_type': 'sales_invoice',
            'invoice_date': str(date.today()),
            'billing_party_id': str(billing_party_id),
            'items': [
                {
                    'description': 'Product 1',
                    'hsn_sac': '421000',
                    'account_id': str(account_id_1),
                    'quantity': 2.0,
                    'unit_price': 500.00,
                    'discount_amount': 50.00,
                    'gst_rate': 18.00
                },
                {
                    'description': 'Product 2',
                    'hsn_sac': '421090',
                    'account_id': str(account_id_2),
                    'quantity': 1.0,
                    'unit_price': 1000.00,
                    'gst_rate': 5.00
                }
            ]
        }

        response = client.post(
            '/invoices',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200

    def test_create_invoice_with_shipping_party(self, client, valid_headers):
        """Test creating invoice with shipping party"""
        account_id = uuid4()
        billing_party_id = uuid4()
        shipping_party_id = uuid4()

        payload = {
            'invoice_type': 'sales_invoice',
            'invoice_date': str(date.today()),
            'billing_party_id': str(billing_party_id),
            'shipping_party_id': str(shipping_party_id),
            'items': [
                {
                    'description': 'Shipped Item',
                    'hsn_sac': '421000',
                    'account_id': str(account_id),
                    'quantity': 1.0,
                    'unit_price': 100.00,
                    'gst_rate': 18.00
                }
            ]
        }

        response = client.post(
            '/invoices',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200

    def test_invoice_response_has_required_fields(self, client, valid_headers):
        """Test that invoice response has all required fields"""
        payload = {
            'invoice_type': 'sales_invoice',
            'invoice_date': str(date.today()),
            'billing_party_id': str(uuid4()),
            'items': [
                {
                    'description': 'Item',
                    'hsn_sac': '421000',
                    'account_id': str(uuid4()),
                    'quantity': 1.0,
                    'unit_price': 100.00,
                    'gst_rate': 18.00
                }
            ]
        }

        response = client.post(
            '/invoices',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        data = response.json()
        assert 'invoice_id' in data
        assert 'invoice_number' in data
        assert 'invoice_type' in data
        assert 'status' in data
        assert 'invoice_grand_total' in data
        assert 'paid_amount' in data
        assert 'balance_due' in data
        assert 'created_at' in data

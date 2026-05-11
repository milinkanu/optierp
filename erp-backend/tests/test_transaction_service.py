"""
Integration tests for transaction_service.py endpoints
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import date

from services.transaction_service import app


class TestTransactionService:
    """Test transaction service endpoints"""

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

    def test_create_transaction_valid(self, client, valid_headers):
        """Test creating a valid transaction"""
        account_id = uuid4()
        party_id = uuid4()

        payload = {
            'txn_type': 'sales_invoice',
            'txn_date': str(date.today()),
            'party_id': str(party_id),
            'line_items': [
                {
                    'account_id': str(account_id),
                    'description': 'Product Sale',
                    'quantity': 1.0,
                    'unit_price': 1000.0,
                    'taxable_amount': 1000.0,
                    'tax_rate': 5.0,
                    'tax_amount': 50.0,
                    'total_amount': 1050.0
                }
            ],
            'meta': {'order_id': 'ORD-001'}
        }

        response = client.post(
            '/transactions',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'transaction_id' in data
        assert 'txn_number' in data
        assert data['txn_type'] == 'sales_invoice'
        assert data['status'] == 'posted'

    def test_create_transaction_without_party(self, client, valid_headers):
        """Test creating a transaction without party_id"""
        account_id = uuid4()

        payload = {
            'txn_type': 'general_journal',
            'txn_date': str(date.today()),
            'line_items': [
                {
                    'account_id': str(account_id),
                    'description': 'Journal Entry',
                    'taxable_amount': 500.0,
                    'tax_rate': 0.0,
                    'tax_amount': 0.0,
                    'total_amount': 500.0
                }
            ]
        }

        response = client.post(
            '/transactions',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'transaction_id' in data

    def test_create_transaction_missing_idempotency_key(self, client, valid_headers):
        """Test creating transaction without idempotency key"""
        account_id = uuid4()

        payload = {
            'txn_type': 'sales_invoice',
            'txn_date': str(date.today()),
            'line_items': [
                {
                    'account_id': str(account_id),
                    'taxable_amount': 1000.0,
                    'tax_rate': 5.0,
                    'tax_amount': 50.0,
                    'total_amount': 1050.0
                }
            ]
        }

        response = client.post(
            '/transactions',
            json=payload,
            headers=valid_headers
        )

        # Should fail because idempotency key is required
        assert response.status_code == 422

    def test_get_transaction(self, client, valid_headers):
        """Test retrieving a transaction"""
        transaction_id = uuid4()

        response = client.get(
            f'/transactions/{transaction_id}',
            headers=valid_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['transaction_id'] == str(transaction_id)
        assert 'txn_number' in data
        assert 'status' in data

    def test_get_transaction_invalid_id(self, client, valid_headers):
        """Test retrieving with invalid transaction ID"""
        response = client.get(
            f'/transactions/invalid-id',
            headers=valid_headers
        )

        # Should fail because invalid UUID format
        assert response.status_code == 422

    def test_reverse_transaction(self, client, valid_headers):
        """Test reversing a transaction"""
        transaction_id = uuid4()

        response = client.post(
            f'/transactions/{transaction_id}/reverse',
            headers=valid_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data['transaction_id'] == str(transaction_id)
        assert data['status'] == 'reversed'
        assert 'reversal_id' in data

    def test_create_transaction_multiple_line_items(self, client, valid_headers):
        """Test creating transaction with multiple line items"""
        account_id_1 = uuid4()
        account_id_2 = uuid4()
        party_id = uuid4()

        payload = {
            'txn_type': 'sales_invoice',
            'txn_date': str(date.today()),
            'party_id': str(party_id),
            'line_items': [
                {
                    'account_id': str(account_id_1),
                    'description': 'Item 1',
                    'quantity': 2.0,
                    'unit_price': 500.0,
                    'taxable_amount': 1000.0,
                    'tax_rate': 5.0,
                    'tax_amount': 50.0,
                    'total_amount': 1050.0
                },
                {
                    'account_id': str(account_id_2),
                    'description': 'Item 2',
                    'quantity': 1.0,
                    'unit_price': 200.0,
                    'taxable_amount': 200.0,
                    'tax_rate': 5.0,
                    'tax_amount': 10.0,
                    'total_amount': 210.0
                }
            ]
        }

        response = client.post(
            '/transactions',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'transaction_id' in data

    def test_transaction_without_auth_headers(self, client):
        """Test transaction endpoint without authentication"""
        payload = {
            'txn_type': 'sales_invoice',
            'txn_date': str(date.today()),
            'line_items': []
        }

        response = client.post(
            '/transactions',
            json=payload,
            headers={'Idempotency-Key': str(uuid4())}
        )

        # Should fail because auth headers are missing
        assert response.status_code == 422

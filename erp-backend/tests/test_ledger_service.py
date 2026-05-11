"""
Integration tests for ledger_service.py endpoints
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import date

from services.ledger_service import app


class TestLedgerService:
    """Test ledger service endpoints"""

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

    def test_create_journal_entry_valid(self, client, valid_headers):
        """Test creating a valid journal entry"""
        account_id = uuid4()

        payload = {
            'journal_type': 'general',
            'journal_date': str(date.today()),
            'reference': 'JNL-001',
            'description': 'Opening Balances',
            'lines': [
                {
                    'account_id': str(account_id),
                    'entry_type': 'debit',
                    'amount': 1000.0,
                    'description': 'Opening balance'
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'journal_id' in data
        assert 'journal_number' in data
        assert data['status'] == 'posted'

    def test_create_journal_with_multiple_lines(self, client, valid_headers):
        """Test creating journal with multiple lines"""
        account_id_1 = uuid4()
        account_id_2 = uuid4()

        payload = {
            'journal_type': 'general',
            'journal_date': str(date.today()),
            'description': 'Multi-line entry',
            'lines': [
                {
                    'account_id': str(account_id_1),
                    'entry_type': 'debit',
                    'amount': 500.0,
                    'description': 'Debit entry'
                },
                {
                    'account_id': str(account_id_2),
                    'entry_type': 'credit',
                    'amount': 500.0,
                    'description': 'Credit entry'
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200

    def test_create_journal_with_party_and_transaction(self, client, valid_headers):
        """Test creating journal with party and transaction references"""
        account_id = uuid4()
        party_id = uuid4()
        transaction_id = uuid4()

        payload = {
            'journal_type': 'payment',
            'journal_date': str(date.today()),
            'reference': 'PAY-001',
            'transaction_id': str(transaction_id),
            'lines': [
                {
                    'account_id': str(account_id),
                    'entry_type': 'credit',
                    'amount': 1000.0,
                    'party_id': str(party_id),
                    'description': 'Payment to vendor'
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'journal_id' in data

    def test_create_journal_missing_idempotency_key(self, client, valid_headers):
        """Test creating journal without idempotency key"""
        payload = {
            'journal_type': 'general',
            'journal_date': str(date.today()),
            'lines': [
                {
                    'account_id': str(uuid4()),
                    'entry_type': 'debit',
                    'amount': 1000.0
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers=valid_headers
        )

        # Should fail because idempotency key is required
        assert response.status_code == 422

    def test_create_journal_invalid_amount(self, client, valid_headers):
        """Test creating journal with invalid amount"""
        payload = {
            'journal_type': 'general',
            'journal_date': str(date.today()),
            'lines': [
                {
                    'account_id': str(uuid4()),
                    'entry_type': 'debit',
                    'amount': 0.0  # Should be > 0
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        # Should fail validation
        assert response.status_code == 422

    def test_create_journal_negative_amount(self, client, valid_headers):
        """Test creating journal with negative amount"""
        payload = {
            'journal_type': 'general',
            'journal_date': str(date.today()),
            'lines': [
                {
                    'account_id': str(uuid4()),
                    'entry_type': 'debit',
                    'amount': -100.0  # Should be > 0
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 422

    def test_journal_response_has_required_fields(self, client, valid_headers):
        """Test that journal response has all required fields"""
        payload = {
            'journal_type': 'general',
            'journal_date': str(date.today()),
            'lines': [
                {
                    'account_id': str(uuid4()),
                    'entry_type': 'debit',
                    'amount': 100.0
                }
            ]
        }

        response = client.post(
            '/ledger/journals',
            json=payload,
            headers={
                **valid_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        data = response.json()
        assert 'journal_id' in data
        assert 'company_id' in data
        assert 'journal_number' in data
        assert 'status' in data
        assert 'created_at' in data

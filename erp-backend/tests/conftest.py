"""
Pytest configuration and fixtures for all tests
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from services.common import create_access_token, JWT_SECRET


@pytest.fixture
def sample_company_id():
    """Generate a sample company ID"""
    return uuid4()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID"""
    return uuid4()


@pytest.fixture
def sample_account_id():
    """Generate a sample account ID"""
    return uuid4()


@pytest.fixture
def sample_party_id():
    """Generate a sample party ID"""
    return uuid4()


@pytest.fixture
def valid_jwt_token(sample_user_id, sample_company_id):
    """Generate a valid JWT token"""
    return create_access_token(
        subject=str(sample_user_id),
        company_id=sample_company_id,
        user_version=1,
        roles=['owner', 'accountant'],
        delegations=[]
    )


@pytest.fixture
def auth_headers(valid_jwt_token, sample_company_id, sample_user_id):
    """Generate valid authentication headers"""
    return {
        'Authorization': f'Bearer {valid_jwt_token}',
        'X-Tenant-ID': str(sample_company_id),
        'X-User-ID': str(sample_user_id),
        'X-User-Roles': 'owner,accountant'
    }


@pytest.fixture
def idempotency_key():
    """Generate an idempotency key"""
    return str(uuid4())


@pytest.fixture
def sample_transaction_payload():
    """Generate sample transaction payload"""
    return {
        'txn_type': 'sales_invoice',
        'txn_date': datetime.now().date().isoformat(),
        'party_id': str(uuid4()),
        'line_items': [
            {
                'account_id': str(uuid4()),
                'description': 'Test Item',
                'quantity': 1.0,
                'unit_price': 1000.0,
                'taxable_amount': 1000.0,
                'tax_rate': 5.0,
                'tax_amount': 50.0,
                'total_amount': 1050.0
            }
        ]
    }


@pytest.fixture
def sample_invoice_payload():
    """Generate sample invoice payload"""
    return {
        'invoice_type': 'sales_invoice',
        'invoice_date': datetime.now().date().isoformat(),
        'due_date': (datetime.now() + timedelta(days=30)).date().isoformat(),
        'billing_party_id': str(uuid4()),
        'currency': 'INR',
        'exchange_rate': 1.0,
        'items': [
            {
                'description': 'Test Product',
                'hsn_sac': '421000',
                'account_id': str(uuid4()),
                'quantity': 1.0,
                'unit_price': 100.00,
                'discount_amount': 0.0,
                'gst_rate': 18.00
            }
        ]
    }

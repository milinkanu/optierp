"""
Integration tests for api_gateway.py endpoints
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from services.api_gateway import app


class TestAPIGateway:
    """Test API gateway endpoints"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'

    def test_health_check_no_auth_required(self, client):
        """Test that health check doesn't require auth headers"""
        # Health check should work without headers
        response = client.get('/health')
        assert response.status_code == 200

    def test_list_services(self, client):
        """Test listing available services"""
        company_id = uuid4()
        user_id = uuid4()

        response = client.get(
            '/services',
            headers={
                'X-Tenant-ID': str(company_id),
                'X-User-ID': str(user_id),
                'X-User-Roles': 'owner'
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'services' in data
        assert isinstance(data['services'], list)
        assert len(data['services']) > 0
        assert 'transaction-service' in data['services']
        assert 'auth-service' in data['services']

    def test_tenant_middleware_missing_tenant_id(self, client):
        """Test middleware with missing X-Tenant-ID header"""
        response = client.get(
            '/services',
            headers={
                'X-User-ID': str(uuid4()),
                'X-User-Roles': 'owner'
            }
        )

        # Should fail because X-Tenant-ID is missing
        assert response.status_code == 401
        data = response.json()
        assert 'detail' in data

    def test_tenant_middleware_missing_user_id(self, client):
        """Test middleware with missing X-User-ID header"""
        response = client.get(
            '/services',
            headers={
                'X-Tenant-ID': str(uuid4()),
                'X-User-Roles': 'owner'
            }
        )

        # Should fail because X-User-ID is missing
        assert response.status_code == 401
        data = response.json()
        assert 'detail' in data

    def test_tenant_middleware_invalid_tenant_id(self, client):
        """Test middleware with invalid X-Tenant-ID format"""
        response = client.get(
            '/services',
            headers={
                'X-Tenant-ID': 'not-a-uuid',
                'X-User-ID': str(uuid4()),
                'X-User-Roles': 'owner'
            }
        )

        # Should fail because tenant ID is not a valid UUID
        assert response.status_code == 401

    def test_tenant_middleware_invalid_user_id(self, client):
        """Test middleware with invalid X-User-ID format"""
        response = client.get(
            '/services',
            headers={
                'X-Tenant-ID': str(uuid4()),
                'X-User-ID': 'not-a-uuid',
                'X-User-Roles': 'owner'
            }
        )

        # Should fail because user ID is not a valid UUID
        assert response.status_code == 401

    def test_tenant_middleware_with_multiple_roles(self, client):
        """Test middleware with multiple roles"""
        response = client.get(
            '/services',
            headers={
                'X-Tenant-ID': str(uuid4()),
                'X-User-ID': str(uuid4()),
                'X-User-Roles': 'owner,accountant,viewer'
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'services' in data

    def test_proxy_endpoint_not_implemented(self, client):
        """Test proxy endpoint returns 501 Not Implemented"""
        response = client.post(
            '/proxy/transaction-service/transactions',
            headers={
                'X-Tenant-ID': str(uuid4()),
                'X-User-ID': str(uuid4()),
                'X-User-Roles': 'owner'
            }
        )

        assert response.status_code == 501
        data = response.json()
        assert 'Gateway proxy is not implemented' in data['detail']

    def test_services_list_contains_expected_services(self, client):
        """Test that services list contains all expected services"""
        response = client.get(
            '/services',
            headers={
                'X-Tenant-ID': str(uuid4()),
                'X-User-ID': str(uuid4())
            }
        )

        data = response.json()
        services = data['services']

        expected_services = [
            'auth-service',
            'transaction-service',
            'ledger-service',
            'ocr-service',
            'compliance-service',
            'bank-reconciliation-service'
        ]

        for service in expected_services:
            assert service in services

    def test_tenant_middleware_optional_roles(self, client):
        """Test middleware works with optional X-User-Roles"""
        response = client.get(
            '/services',
            headers={
                'X-Tenant-ID': str(uuid4()),
                'X-User-ID': str(uuid4())
            }
        )

        # Should work without roles header
        assert response.status_code == 200

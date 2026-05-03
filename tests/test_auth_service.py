"""
Integration tests for auth_service.py endpoints
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from uuid import uuid4
from jose import jwt

from services.auth_service import app, LoginRequest, LoginResponse
from services.common import JWT_ALGORITHM, JWT_SECRET


class TestAuthService:
    """Test authentication service endpoints"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)

    def test_login_endpoint(self, client):
        """Test login endpoint with valid credentials"""
        response = client.post(
            '/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'testpassword123'
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['token_type'] == 'Bearer'
        assert len(data['access_token']) > 0

    def test_login_invalid_email(self, client):
        """Test login with invalid email format"""
        response = client.post(
            '/auth/login',
            json={
                'email': 'invalid-email',
                'password': 'testpassword123'
            }
        )

        # Should fail validation
        assert response.status_code == 422

    def test_login_missing_fields(self, client):
        """Test login with missing required fields"""
        response = client.post(
            '/auth/login',
            json={'email': 'test@example.com'}
        )

        assert response.status_code == 422

    def test_refresh_token_endpoint(self, client):
        """Test token refresh endpoint"""
        # First, login to get a token
        login_response = client.post(
            '/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'testpassword123'
            }
        )

        access_token = login_response.json()['access_token']
        claims = jwt.decode(access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        company_id = claims['company_id']

        # Try to refresh the token
        refresh_response = client.post(
            '/auth/refresh',
            headers={
                'Authorization': f'Bearer {access_token}',
                'X-Tenant-ID': company_id,
                'X-User-ID': str(uuid4()),
                'X-User-Roles': 'owner'
            }
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert 'access_token' in data
        assert data['token_type'] == 'Bearer'

    def test_refresh_token_missing_headers(self, client):
        """Test refresh with missing headers"""
        login_response = client.post(
            '/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'testpassword123'
            }
        )

        access_token = login_response.json()['access_token']

        refresh_response = client.post(
            '/auth/refresh',
            headers={
                'Authorization': f'Bearer {access_token}'
            }
        )

        # Should fail because required headers are missing
        assert refresh_response.status_code in [401, 422]

    def test_token_returns_bearer_type(self, client):
        """Test that login returns Bearer token type"""
        response = client.post(
            '/auth/login',
            json={
                'email': 'user@test.com',
                'password': 'password123'
            }
        )

        data = response.json()
        assert data['token_type'] == 'Bearer'

    def test_login_response_has_all_fields(self, client):
        """Test LoginResponse schema"""
        response = client.post(
            '/auth/login',
            json={
                'email': 'test@example.com',
                'password': 'testpassword123'
            }
        )

        data = response.json()
        assert 'access_token' in data
        assert 'token_type' in data
        assert isinstance(data['access_token'], str)
        assert isinstance(data['token_type'], str)

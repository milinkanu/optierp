"""
Unit tests for common.py - JWT, auth, and context functions
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from jose import jwt, JWTError
from fastapi import HTTPException

from services.common import (
    TenantContext,
    TokenPayload,
    create_access_token,
    verify_jwt_token,
    JWT_SECRET,
    JWT_ALGORITHM,
)


class TestJWTFunctions:
    """Test JWT creation and verification"""

    def test_create_access_token(self):
        """Test creating a valid JWT token"""
        user_id = str(uuid4())
        company_id = uuid4()
        user_version = 1
        roles = ['owner', 'accountant']
        delegations = []

        token = create_access_token(
            subject=user_id,
            company_id=company_id,
            user_version=user_version,
            roles=roles,
            delegations=delegations
        )

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_jwt_token_valid(self):
        """Test verifying a valid token"""
        user_id = str(uuid4())
        company_id = uuid4()
        user_version = 1
        roles = ['owner']
        delegations = []

        token = create_access_token(
            subject=user_id,
            company_id=company_id,
            user_version=user_version,
            roles=roles,
            delegations=delegations
        )

        payload = verify_jwt_token(token)

        assert payload.sub == user_id
        assert str(payload.company_id) == str(company_id)
        assert payload.user_version == user_version
        assert payload.roles == roles

    def test_verify_jwt_token_invalid(self):
        """Test verifying an invalid token"""
        with pytest.raises(HTTPException):
            verify_jwt_token("invalid.token.here")

    def test_jwt_token_expiration(self):
        """Test that JWT tokens include expiration"""
        user_id = str(uuid4())
        company_id = uuid4()

        token = create_access_token(
            subject=user_id,
            company_id=company_id,
            user_version=1,
            roles=['owner'],
            delegations=[]
        )

        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert 'exp' in decoded
        assert decoded['exp'] > datetime.utcnow().timestamp()

    def test_token_payload_model(self):
        """Test TokenPayload model validation"""
        user_id = str(uuid4())
        company_id = uuid4()

        payload_dict = {
            'sub': user_id,
            'company_id': str(company_id),
            'user_version': 1,
            'roles': ['owner'],
            'delegations': [],
            'exp': int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        }

        payload = TokenPayload(**payload_dict)
        assert payload.sub == user_id
        assert payload.user_version == 1

    def test_tenant_context_model(self):
        """Test TenantContext model"""
        company_id = uuid4()
        user_id = uuid4()
        roles = ['owner', 'accountant']

        context = TenantContext(
            company_id=company_id,
            user_id=user_id,
            roles=roles
        )

        assert context.company_id == company_id
        assert context.user_id == user_id
        assert context.roles == roles

    def test_multiple_roles_in_token(self):
        """Test token with multiple roles"""
        roles = ['owner', 'accountant', 'viewer']

        token = create_access_token(
            subject=str(uuid4()),
            company_id=uuid4(),
            user_version=1,
            roles=roles,
            delegations=[]
        )

        payload = verify_jwt_token(token)
        assert len(payload.roles) == 3
        assert 'owner' in payload.roles

    def test_delegations_in_token(self):
        """Test token with delegations"""
        delegations = [
            {'role': 'accountant', 'end_date': '2026-12-31'},
            {'role': 'viewer', 'end_date': '2026-06-30'}
        ]

        token = create_access_token(
            subject=str(uuid4()),
            company_id=uuid4(),
            user_version=1,
            roles=['owner'],
            delegations=delegations
        )

        payload = verify_jwt_token(token)
        assert len(payload.delegations) == 2

# Testing Guide for FinOps Project

## Overview

This document provides comprehensive guidance on running and understanding the test suite for the FinOps project.

## Test Suite Structure

The test suite consists of 9 main test files covering different services and functionality:

### 1. test_common.py - Core Utilities Testing
**File**: `tests/test_common.py`
**Coverage**: JWT token generation, verification, and authentication context

**Tests**:
- `test_create_access_token`: Verifies JWT token creation
- `test_verify_jwt_token_valid`: Tests token verification with valid token
- `test_verify_jwt_token_invalid`: Tests error handling for invalid tokens
- `test_jwt_token_expiration`: Ensures tokens include proper expiration
- `test_token_payload_model`: Validates TokenPayload model
- `test_tenant_context_model`: Validates TenantContext model
- `test_multiple_roles_in_token`: Tests tokens with multiple roles
- `test_delegations_in_token`: Tests token delegation tracking

**Run**: `pytest tests/test_common.py -v`

---

### 2. test_auth_service.py - Authentication Endpoints
**File**: `tests/test_auth_service.py`
**Coverage**: Login and token refresh endpoints

**Tests**:
- `test_login_endpoint`: Valid login request
- `test_login_invalid_email`: Email format validation
- `test_login_missing_fields`: Required field validation
- `test_refresh_token_endpoint`: Token refresh flow
- `test_refresh_token_missing_headers`: Header validation
- `test_token_returns_bearer_type`: Response format validation
- `test_login_response_has_all_fields`: Response schema validation

**Run**: `pytest tests/test_auth_service.py -v`

---

### 3. test_api_gateway.py - API Gateway & Middleware
**File**: `tests/test_api_gateway.py`
**Coverage**: Gateway endpoints, tenant middleware, service discovery

**Tests**:
- `test_health_check`: Health endpoint without authentication
- `test_health_check_no_auth_required`: Health check accessibility
- `test_list_services`: Service discovery endpoint
- `test_tenant_middleware_missing_tenant_id`: Missing header handling
- `test_tenant_middleware_missing_user_id`: Missing user header
- `test_tenant_middleware_invalid_tenant_id`: UUID validation
- `test_tenant_middleware_invalid_user_id`: User UUID validation
- `test_tenant_middleware_with_multiple_roles`: Multiple role support
- `test_proxy_endpoint_not_implemented`: Proxy status validation
- `test_services_list_contains_expected_services`: Service list completeness
- `test_tenant_middleware_optional_roles`: Optional role header handling

**Run**: `pytest tests/test_api_gateway.py -v`

---

### 4. test_transaction_service.py - Transaction Management
**File**: `tests/test_transaction_service.py`
**Coverage**: Transaction creation, retrieval, and reversal

**Tests**:
- `test_create_transaction_valid`: Create valid transaction
- `test_create_transaction_without_party`: Party optional handling
- `test_create_transaction_missing_idempotency_key`: Idempotency enforcement
- `test_get_transaction`: Retrieve existing transaction
- `test_get_transaction_invalid_id`: Invalid UUID handling
- `test_reverse_transaction`: Transaction reversal
- `test_create_transaction_multiple_line_items`: Multi-line items support
- `test_transaction_without_auth_headers`: Authentication enforcement

**Run**: `pytest tests/test_transaction_service.py -v`

---

### 5. test_invoice_service.py - Invoice Management
**File**: `tests/test_invoice_service.py`
**Coverage**: Invoice creation, validation, tax calculations

**Tests**:
- `test_create_sales_invoice_valid`: Create sales invoice
- `test_create_purchase_invoice_valid`: Create purchase invoice
- `test_create_invoice_invalid_type`: Invoice type validation
- `test_create_invoice_no_line_items`: Line item requirement
- `test_create_invoice_with_tds_tcs`: Tax calculations
- `test_create_invoice_multiple_items`: Multi-item invoices
- `test_create_invoice_with_shipping_party`: Shipping address handling
- `test_invoice_response_has_required_fields`: Response schema validation

**Run**: `pytest tests/test_invoice_service.py -v`

---

### 6. test_ledger_service.py - Ledger & Journal Entries
**File**: `tests/test_ledger_service.py`
**Coverage**: Journal entry creation and ledger management

**Tests**:
- `test_create_journal_entry_valid`: Create valid journal entry
- `test_create_journal_with_multiple_lines`: Multi-line journal entries
- `test_create_journal_with_party_and_transaction`: References handling
- `test_create_journal_missing_idempotency_key`: Idempotency enforcement
- `test_create_journal_invalid_amount`: Amount validation
- `test_create_journal_negative_amount`: Negative amount rejection
- `test_journal_response_has_required_fields`: Response schema validation

**Run**: `pytest tests/test_ledger_service.py -v`

---

### 7. test_onboarding_service.py - Company Onboarding
**File**: `tests/test_onboarding_service.py`
**Coverage**: KYC validation, encryption, and onboarding workflows

**Tests**:
- `test_validate_gstin_checksum_valid`: GSTIN validation
- `test_validate_gstin_checksum_invalid`: Invalid GSTIN rejection
- `test_extract_pan_from_gstin`: PAN extraction logic
- `test_encrypt_decrypt_pan`: PAN encryption/decryption
- `test_api_onboarding_request_model_valid`: Onboarding request validation
- `test_api_onboarding_request_invalid_phone`: Phone format validation
- `test_api_onboarding_request_invalid_pan_length`: PAN length validation
- `test_ocr_upload_request_model`: OCR upload request validation
- `test_onboarding_job_status_model`: Job status model validation
- `test_onboarding_confirmation_request_model`: Confirmation model validation
- `test_api_onboarding_response_model`: Response model validation

**Run**: `pytest tests/test_onboarding_service.py -v`

---

### 8. test_ocr_service.py - Document Processing
**File**: `tests/test_ocr_service.py`
**Coverage**: OCR processing, document types, confidence tracking

**Tests**:
- `test_document_type_enum_values`: Document type enumeration
- `test_ocr_mode_enum_values`: OCR mode enumeration
- `test_document_upload_request_model`: Upload request validation
- `test_document_response_model`: Response model validation
- `test_ocr_process_request_model`: Process request validation
- `test_ocr_result_response_model`: Result response validation
- `test_credit_balance_response_model`: Credit balance model
- `test_confirm_ocr_request_model`: Confirmation model validation
- `test_ocr_result_with_partial_confidence`: Partial confidence handling
- `test_ocr_result_failed_status`: Error handling in results

**Run**: `pytest tests/test_ocr_service.py -v`

---

### 9. test_compliance_service.py - Tax Compliance
**File**: `tests/test_compliance_service.py`
**Coverage**: Tax configuration, compliance reporting, rate validation

**Tests**:
- `test_tax_rate_config_model_gst`: GST rate configuration
- `test_tax_rate_config_model_tds`: TDS rate configuration
- `test_tax_rate_config_invalid_type`: Tax type validation
- `test_tax_rate_config_rate_validation`: Rate range validation
- `test_tax_rule_config_model`: Tax rule model
- `test_gst_liability_model`: GST liability tracking
- `test_gst_liability_component_validation`: GST component validation
- `test_gst_return_request_model`: GST return request
- `test_gst_return_response_model`: GST return response
- `test_tds_deduction_model`: TDS deduction model
- `test_tds_return_request_model`: TDS return request
- `test_tcs_collection_model`: TCS collection model
- `test_gst_return_period_format`: Period format validation
- `test_tds_return_quarter_format`: Quarter format validation

**Run**: `pytest tests/test_compliance_service.py -v`

---

### 10. test_examples.py - End-to-End Examples
**File**: `tests/test_examples.py`
**Coverage**: Complete workflow demonstrations

**Tests**:
- `test_complete_workflow_example`: Invoice creation workflow
- `test_transaction_and_ledger_workflow`: Transaction to ledger workflow

**Run**: `pytest tests/test_examples.py -v`

---

## Running Tests

### Run All Tests
```bash
pytest
```

### Run with Verbose Output
```bash
pytest -v
```

### Run with Coverage Report
```bash
pytest --cov=services --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Specific Service Tests
```bash
pytest tests/test_auth_service.py          # Auth tests only
pytest tests/test_invoice_service.py       # Invoice tests only
pytest tests/test_compliance_service.py    # Compliance tests only
```

### Run Specific Test Function
```bash
pytest tests/test_auth_service.py::TestAuthService::test_login_endpoint
```

### Run Tests Matching Pattern
```bash
pytest -k "invoice"                        # Run all tests with 'invoice' in name
pytest -k "test_create"                    # Run all tests with 'test_create' in name
```

### Run Tests in Parallel
```bash
pytest -n auto                             # Uses all available CPU cores
pytest -n 4                                # Uses 4 processes
```

### Run with Live Output
```bash
pytest -s                                  # Shows print statements
pytest -vv                                 # Extra verbose
```

### Watch Mode (Re-run on Changes)
```bash
ptw                                        # Watch and run tests
ptw -- -v                                  # Watch with verbose output
```

## Test Fixtures

### Built-in Fixtures (from conftest.py)

```python
# Generate sample company ID
@pytest.fixture
def sample_company_id():
    return uuid4()

# Generate sample user ID
@pytest.fixture
def sample_user_id():
    return uuid4()

# Generate valid JWT token
@pytest.fixture
def valid_jwt_token(sample_user_id, sample_company_id):
    return create_access_token(...)

# Generate auth headers for requests
@pytest.fixture
def auth_headers(valid_jwt_token, sample_company_id, sample_user_id):
    return {
        'Authorization': f'Bearer {valid_jwt_token}',
        'X-Tenant-ID': str(sample_company_id),
        'X-User-ID': str(sample_user_id)
    }
```

### Using Fixtures in Tests

```python
def test_example(auth_headers, sample_transaction_payload):
    # auth_headers is automatically injected
    # sample_transaction_payload is automatically injected
    response = client.post(
        '/transactions',
        json=sample_transaction_payload,
        headers=auth_headers
    )
```

## Common Test Patterns

### Testing Valid Request
```python
def test_create_valid_resource(client, auth_headers):
    payload = {'field': 'value'}
    response = client.post(
        '/endpoint',
        json=payload,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert 'id' in data
```

### Testing Validation Error
```python
def test_invalid_input(client, auth_headers):
    payload = {'field': None}  # Invalid
    response = client.post(
        '/endpoint',
        json=payload,
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error
```

### Testing Authentication
```python
def test_missing_auth(client):
    response = client.post(
        '/endpoint',
        json={'field': 'value'}
        # No headers - should fail
    )
    assert response.status_code == 422  # or 401
```

### Testing Authorization
```python
def test_insufficient_permission(client):
    headers = auth_headers.copy()
    headers['X-User-Roles'] = 'viewer'  # Limited role
    response = client.post(
        '/admin/endpoint',
        json={},
        headers=headers
    )
    assert response.status_code == 403  # Forbidden
```

## Troubleshooting Tests

### Test Fails with "Module not found"
```bash
pip install -r services/requirements.txt
pip install -r requirements-dev.txt
```

### Database Connection Error
```bash
# Ensure PostgreSQL is running
# Check database URL in .env
psql -U finops -d finops -c "SELECT 1;"
```

### UUID Generation Issues
```python
# Instead of string
transaction_id = uuid4()
# Use in JSON
"transaction_id": str(transaction_id)
```

### Async Test Failures
```bash
# Install asyncio support
pip install pytest-asyncio
# Or update pytest.ini
[pytest]
asyncio_mode = auto
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=services
```

## Performance Optimization

### Running Only Changed Tests
```bash
# If you have git tracking
pytest --lf                               # Last failed
pytest --ff                               # Failed first
```

### Reducing Test Execution Time
```bash
# Run in parallel
pytest -n auto

# Run specific test category
pytest -m "not slow"

# Skip slow tests
pytest -m "not integration"
```

## Test Maintenance

### Update Tests When Code Changes
1. Run all tests: `pytest`
2. Identify failing tests
3. Update test expectations or fix code
4. Re-run tests until all pass

### Keep Tests DRY
- Use fixtures for common setup
- Create helper functions for repeated patterns
- Use parameterize for testing multiple scenarios

```python
@pytest.mark.parametrize("invoice_type,expected_status", [
    ("sales_invoice", "draft"),
    ("purchase_invoice", "draft"),
])
def test_invoice_creation(invoice_type, expected_status):
    # Test multiple scenarios
    pass
```

## Best Practices

1. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   # Arrange
   payload = {...}
   # Act
   response = client.post(...)
   # Assert
   assert response.status_code == 200
   ```

2. **One assertion per test**: Keep tests focused
3. **Descriptive names**: Use `test_what_when_then()` format
4. **Test edge cases**: Not just happy paths
5. **Keep tests independent**: No test should depend on another
6. **Mock external services**: Don't test third-party code
7. **Use fixtures**: Avoid code duplication
8. **Document complex tests**: Add comments explaining purpose

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)

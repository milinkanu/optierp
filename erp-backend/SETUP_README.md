# FinOps Project Setup and Test Guide

## Project Overview

FinOps is a comprehensive Financial Operating System built with FastAPI, designed to handle multi-tenant financial operations including transactions, invoices, ledger entries, compliance management, and OCR-based document processing.

### Key Features

- **Multi-tenant Architecture**: Secure tenant isolation with PostgreSQL Row-Level Security (RLS)
- **Authentication & Authorization**: JWT-based authentication with role-based access control
- **Transaction Management**: Create, retrieve, and reverse transactions with idempotency support
- **Invoice Processing**: Full invoice lifecycle management with tax calculations
- **Ledger Management**: Double-entry bookkeeping with immutable audit trails
- **OCR Integration**: Document scanning and data extraction using PaddleOCR and VLM
- **Compliance Engine**: GST, TDS, TCS, and tax compliance tracking
- **Onboarding Service**: Company onboarding with KYC verification

## Prerequisites

- **Python**: 3.9 or higher
- **PostgreSQL**: 13 or higher (for production)
- **pip**: Python package manager
- **Git**: Version control

## Project Structure

```
optierp4/
├── services/
│   ├── __init__.py
│   ├── api_gateway.py          # API Gateway with middleware
│   ├── auth_service.py         # Authentication service
│   ├── common.py               # Shared utilities (JWT, contexts)
│   ├── compliance_service.py   # Compliance & tax management
│   ├── invoice_service.py      # Invoice management
│   ├── ledger_service.py       # Ledger & journal entries
│   ├── ocr_service.py          # OCR & document processing
│   ├── onboarding_service.py   # Company onboarding
│   ├── transaction_service.py  # Transaction management
│   └── requirements.txt        # Python dependencies
├── database/
│   ├── schema.sql              # Main schema
│   ├── compliance_schema.sql   # Compliance tables
│   ├── compliance_setup.sql    # Compliance setup
│   ├── ocr_credit_schema.sql   # OCR credit schema
│   └── transaction_invoice_schema.sql  # Transaction/Invoice schema
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures and configuration
│   ├── test_common.py          # Tests for common utilities
│   ├── test_auth_service.py    # Authentication tests
│   ├── test_api_gateway.py     # API Gateway tests
│   ├── test_transaction_service.py  # Transaction tests
│   ├── test_invoice_service.py # Invoice tests
│   ├── test_ledger_service.py  # Ledger tests
│   ├── test_onboarding_service.py   # Onboarding tests
│   ├── test_ocr_service.py     # OCR tests
│   └── test_compliance_service.py   # Compliance tests
├── docs/
│   ├── COMPLIANCE_ENGINE_README.md
│   ├── OCR_CREDIT_SYSTEM.md
│   └── ONBOARDING.md
├── pytest.ini                  # Pytest configuration
├── README.md                   # This file
├── rules.md                    # Project rules and guidelines
└── inspect_schema.py           # Database schema inspection tool
```

## Installation and Setup

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd optierp4
```

### Step 2: Create a Virtual Environment

It's recommended to use a virtual environment to isolate project dependencies.

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
cd services
pip install -r requirements.txt
cd ..
```

### Step 4: Install Additional Testing Dependencies

```bash
pip install pytest pytest-asyncio httpx
```

### Step 5: Set Up PostgreSQL Database

#### Local PostgreSQL Setup

1. **Start PostgreSQL Server**
   - On Windows: Use PostgreSQL installer or run from Services
   - On macOS: `brew services start postgresql`
   - On Linux: `sudo systemctl start postgresql`

2. **Create Database and User**

```bash
# Connect to PostgreSQL
psql -U postgres

# In psql shell
CREATE USER finops WITH PASSWORD 'finops_password';
CREATE DATABASE finops OWNER finops;
ALTER ROLE finops SET client_encoding TO 'utf8';
ALTER ROLE finops SET default_transaction_isolation TO 'read committed';
ALTER ROLE finops SET default_transaction_deferrable TO on;
ALTER ROLE finops SET timezone TO 'UTC';
```

3. **Apply Schema**

```bash
# Connect to the finops database
psql -U finops -d finops -f database/schema.sql
psql -U finops -d finops -f database/compliance_schema.sql
psql -U finops -d finops -f database/compliance_setup.sql
psql -U finops -d finops -f database/ocr_credit_schema.sql
psql -U finops -d finops -f database/transaction_invoice_schema.sql
```

### Step 6: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://finops:finops_password@localhost:5432/finops

# JWT
JWT_SECRET=your_super_secret_key_min_32_chars_long
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# API
API_HOST=127.0.0.1
API_PORT=8000

# OCR
OCR_ENABLED=true
PADDLEOCR_LANG=en
VLM_ENABLED=false

# File uploads
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=104857600  # 100MB in bytes
```

**Important**: Never commit the `.env` file. Add it to `.gitignore`.

### Step 7: Verify Installation

```bash
# Check all dependencies are installed
pip list

# Verify PostgreSQL connection
psql -U finops -d finops -c "SELECT 1;"
```

## Running the Application

### Start Individual Services

Each service runs as a separate FastAPI application:

```bash
# Terminal 1: Start API Gateway
uvicorn services.api_gateway:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Auth Service
uvicorn services.auth_service:app --host 0.0.0.0 --port 8001

# Terminal 3: Start Transaction Service
uvicorn services.transaction_service:app --host 0.0.0.0 --port 8002

# Terminal 4: Start Invoice Service
uvicorn services.invoice_service:app --host 0.0.0.0 --port 8003

# Terminal 5: Start Ledger Service
uvicorn services.ledger_service:app --host 0.0.0.0 --port 8004

# Terminal 6: Start OCR Service
uvicorn services.ocr_service:app --host 0.0.0.0 --port 8005

# Terminal 7: Start Compliance Service
uvicorn services.compliance_service:app --host 0.0.0.0 --port 8006

# Terminal 8: Start Onboarding Service
uvicorn services.onboarding_service:app --host 0.0.0.0 --port 8007
```

### Access API Documentation

- **API Gateway**: http://localhost:8000/docs
- **Auth Service**: http://localhost:8001/docs
- **Transaction Service**: http://localhost:8002/docs
- **Invoice Service**: http://localhost:8003/docs
- **Ledger Service**: http://localhost:8004/docs
- **OCR Service**: http://localhost:8005/docs
- **Compliance Service**: http://localhost:8006/docs
- **Onboarding Service**: http://localhost:8007/docs

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
# Test common utilities
pytest tests/test_common.py

# Test authentication service
pytest tests/test_auth_service.py

# Test API gateway
pytest tests/test_api_gateway.py

# Test transaction service
pytest tests/test_transaction_service.py

# Test invoice service
pytest tests/test_invoice_service.py

# Test ledger service
pytest tests/test_ledger_service.py

# Test onboarding service
pytest tests/test_onboarding_service.py

# Test OCR service
pytest tests/test_ocr_service.py

# Test compliance service
pytest tests/test_compliance_service.py
```

### Run Specific Test Function

```bash
pytest tests/test_auth_service.py::TestAuthService::test_login_endpoint
```

### Run Tests with Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only auth tests
pytest -m auth

# Run only transaction tests
pytest -m transaction
```

### Run Tests with Coverage

```bash
# Install coverage tool
pip install pytest-cov

# Run with coverage report
pytest --cov=services --cov-report=html
```

## Test Organization

### Test Files

1. **test_common.py**: Tests for JWT, authentication context, and shared utilities
   - JWT token creation and verification
   - Token payload validation
   - TenantContext model validation
   - Permission checking

2. **test_auth_service.py**: Authentication service endpoints
   - Login endpoint
   - Token refresh endpoint
   - Header validation

3. **test_api_gateway.py**: API Gateway middleware and endpoints
   - Health check
   - Service listing
   - Tenant middleware validation
   - Header enforcement

4. **test_transaction_service.py**: Transaction management
   - Create transaction
   - Get transaction
   - Reverse transaction
   - Idempotency handling
   - Multi-line item transactions

5. **test_invoice_service.py**: Invoice management
   - Create sales invoice
   - Create purchase invoice
   - Invoice validation
   - Multiple line items
   - Tax calculations

6. **test_ledger_service.py**: Journal and ledger entries
   - Create journal entry
   - Multiple line items
   - Party and transaction references
   - Amount validation

7. **test_onboarding_service.py**: Company onboarding
   - GSTIN validation
   - PAN encryption/decryption
   - Document upload
   - Company confirmation

8. **test_ocr_service.py**: OCR document processing
   - Document type enums
   - OCR mode handling
   - Extracted data validation
   - Credit balance tracking

9. **test_compliance_service.py**: Tax compliance
   - GST rate configuration
   - TDS deduction tracking
   - TCS collection
   - Tax return creation

### Test Fixtures (conftest.py)

Common fixtures available for all tests:

- `sample_company_id`: Sample UUID for company
- `sample_user_id`: Sample UUID for user
- `sample_account_id`: Sample UUID for account
- `sample_party_id`: Sample UUID for party
- `valid_jwt_token`: Valid JWT token
- `auth_headers`: Valid authentication headers
- `idempotency_key`: Idempotency key for requests
- `sample_transaction_payload`: Sample transaction data
- `sample_invoice_payload`: Sample invoice data

## API Endpoint Examples

### Authentication

```bash
# Login
curl -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'

# Refresh Token
curl -X POST "http://localhost:8001/auth/refresh" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <company-id>" \
  -H "X-User-ID: <user-id>"
```

### Create Transaction

```bash
curl -X POST "http://localhost:8002/transactions" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <company-id>" \
  -H "X-User-ID: <user-id>" \
  -H "Idempotency-Key: <unique-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "txn_type": "sales_invoice",
    "txn_date": "2026-05-03",
    "party_id": "<party-id>",
    "line_items": [
      {
        "account_id": "<account-id>",
        "description": "Product Sale",
        "quantity": 1.0,
        "unit_price": 1000.0,
        "taxable_amount": 1000.0,
        "tax_rate": 5.0,
        "tax_amount": 50.0,
        "total_amount": 1050.0
      }
    ]
  }'
```

### Create Invoice

```bash
curl -X POST "http://localhost:8003/invoices" \
  -H "Authorization: Bearer <access_token>" \
  -H "X-Tenant-ID: <company-id>" \
  -H "X-User-ID: <user-id>" \
  -H "Idempotency-Key: <unique-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_type": "sales_invoice",
    "invoice_date": "2026-05-03",
    "billing_party_id": "<party-id>",
    "items": [
      {
        "description": "Product A",
        "hsn_sac": "421000",
        "account_id": "<account-id>",
        "quantity": 5.0,
        "unit_price": 100.00,
        "gst_rate": 18.00
      }
    ]
  }'
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Error

```
Error: psycopg.OperationalError: connection failed
```

**Solution:**
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure database and user exist
- Check firewall settings

#### 2. Missing Dependencies

```
Error: ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**
```bash
pip install -r services/requirements.txt
```

#### 3. JWT Token Invalid

```
Error: Invalid authentication credentials
```

**Solution:**
- Verify JWT_SECRET is configured correctly
- Check token hasn't expired
- Ensure Authorization header format: "Bearer <token>"

#### 4. Tenant Headers Missing

```
Error: Missing or invalid tenant headers
```

**Solution:**
- Include all required headers:
  - `X-Tenant-ID` (company UUID)
  - `X-User-ID` (user UUID)
  - `Authorization: Bearer <token>`

#### 5. Port Already in Use

```
Error: Address already in use
```

**Solution:**
```bash
# Change port in uvicorn command
uvicorn services.api_gateway:app --host 0.0.0.0 --port 8080
```

## Development Workflow

### Making Changes

1. Create a feature branch
2. Make your changes
3. Run tests to ensure nothing breaks
4. Update documentation if needed
5. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Write docstrings for classes and functions
- Keep functions small and focused

### Testing Requirements

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage
- Test both happy path and error cases

## Useful Commands

```bash
# Run specific test with verbose output
pytest tests/test_auth_service.py -v

# Run tests and show print statements
pytest -s tests/test_transaction_service.py

# Run tests with specific marker
pytest -m "transaction and not slow"

# Generate coverage report
pytest --cov=services --cov-report=term-missing

# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -n auto

# Watch for changes and re-run tests (requires pytest-watch)
pip install pytest-watch
ptw

# Profile test execution
pytest --durations=10
```

## Performance Optimization

### Database Optimization

1. Create indexes for frequently queried columns:
```sql
CREATE INDEX idx_transactions_company_id ON transactions(company_id);
CREATE INDEX idx_invoices_billing_party_id ON invoices(billing_party_id);
CREATE INDEX idx_ledger_entries_account_id ON ledger_entries(account_id);
```

2. Enable connection pooling in `services/common.py`:
```python
from sqlalchemy.pool import QueuePool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

### API Performance

1. Add response caching for frequently accessed data
2. Use async/await for I/O operations
3. Implement pagination for large result sets
4. Add request/response compression (gzip)

## Security Considerations

1. **Never commit secrets**: Use .env files and add to .gitignore
2. **Validate all inputs**: Use Pydantic models for validation
3. **Use HTTPS in production**: Configure SSL certificates
4. **Rotate JWT secrets regularly**: Update JWT_SECRET periodically
5. **Implement rate limiting**: Prevent brute force attacks
6. **Use environment-specific secrets**: Different secrets for dev/prod
7. **Enable CORS carefully**: Only allow trusted origins

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM Tutorial](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Python JWT Documentation](https://python-jose.readthedocs.io/)

## Support and Contact

For issues, questions, or contributions:
- Create an issue on the project repository
- Contact the development team
- Review the documentation in the `docs/` folder

## License

[Add your license information here]

## Changelog

### Version 1.0.0 (May 2026)
- Initial project structure
- Core services implementation
- Comprehensive test suite
- Setup documentation

---

**Last Updated**: May 3, 2026
**Status**: Active Development

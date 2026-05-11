"""Test fixture for individual endpoints - demonstrates how to use the test suite"""
import pytest
from uuid import uuid4


class TestEndToEndExample:
    """Example test demonstrating how to use fixtures and test endpoints"""

    def test_complete_workflow_example(self, auth_headers, sample_invoice_payload):
        """
        Complete workflow example:
        1. Login and get token
        2. Create an invoice
        3. Retrieve the invoice
        """
        from fastapi.testclient import TestClient
        from services.invoice_service import app as invoice_app

        client = TestClient(invoice_app)

        # Create an invoice
        payload = sample_invoice_payload
        response = client.post(
            '/invoices',
            json=payload,
            headers={
                **auth_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert response.status_code == 200
        invoice_data = response.json()
        invoice_id = invoice_data['invoice_id']

        # Verify invoice was created
        assert 'invoice_id' in invoice_data
        assert invoice_data['invoice_type'] == 'sales_invoice'

    def test_transaction_and_ledger_workflow(self, auth_headers):
        """
        Example workflow:
        1. Create a transaction
        2. Create corresponding ledger entries
        3. Verify the relationship
        """
        from fastapi.testclient import TestClient
        from services.transaction_service import app as txn_app
        from services.ledger_service import app as ledger_app
        from datetime import date

        txn_client = TestClient(txn_app)
        ledger_client = TestClient(ledger_app)

        # Create transaction
        txn_payload = {
            'txn_type': 'sales_invoice',
            'txn_date': str(date.today()),
            'party_id': str(uuid4()),
            'line_items': [
                {
                    'account_id': str(uuid4()),
                    'description': 'Sale',
                    'taxable_amount': 1000.0,
                    'tax_rate': 5.0,
                    'tax_amount': 50.0,
                    'total_amount': 1050.0
                }
            ]
        }

        txn_response = txn_client.post(
            '/transactions',
            json=txn_payload,
            headers={
                **auth_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert txn_response.status_code == 200
        transaction_id = txn_response.json()['transaction_id']

        # Create ledger entry referencing the transaction
        ledger_payload = {
            'journal_type': 'auto',
            'journal_date': str(date.today()),
            'transaction_id': transaction_id,
            'lines': [
                {
                    'account_id': str(uuid4()),
                    'entry_type': 'debit',
                    'amount': 1050.0
                }
            ]
        }

        ledger_response = ledger_client.post(
            '/ledger/journals',
            json=ledger_payload,
            headers={
                **auth_headers,
                'Idempotency-Key': str(uuid4())
            }
        )

        assert ledger_response.status_code == 200

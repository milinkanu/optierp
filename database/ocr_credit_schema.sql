-- OCR and Credit System Schema Additions

-- Enums for OCR and Credit
CREATE TYPE ocr_mode_enum AS ENUM ('manual', 'ocr', 'smart');
CREATE TYPE credit_transaction_type_enum AS ENUM ('subscription', 'pay_as_you_go', 'bonus', 'deduction');
CREATE TYPE document_type_enum AS ENUM ('invoice', 'receipt', 'bank_statement', 'kyc', 'other');

-- Documents table for uploaded source documents
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    document_type document_type_enum NOT NULL,
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL, -- Object storage URL
    file_size BIGINT NOT NULL,
    mime_type TEXT NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES users(user_id),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    checksum TEXT NOT NULL -- For integrity
);

-- OCR Results table
CREATE TABLE ocr_results (
    ocr_result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    company_id UUID NOT NULL,
    mode ocr_mode_enum NOT NULL,
    paddleocr_confidence NUMERIC(5,4),
    vlm_confidence NUMERIC(5,4),
    extracted_data JSONB,
    ocr_metadata JSONB, -- Contains processing details, timestamps, etc.
    status ocr_status_enum NOT NULL DEFAULT 'pending',
    processed_at TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,
    confirmed_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Credit Ledger for tenant credits
CREATE TABLE credit_ledger (
    credit_entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_type credit_transaction_type_enum NOT NULL,
    amount NUMERIC(18,2) NOT NULL, -- Positive for credit, negative for debit
    balance_after NUMERIC(18,2) NOT NULL,
    reference_type TEXT, -- e.g., 'ocr_result', 'subscription'
    reference_id UUID,
    description TEXT,
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add credit balance to companies
ALTER TABLE companies ADD COLUMN credit_balance NUMERIC(18,2) NOT NULL DEFAULT 0;

-- Indexes
CREATE INDEX idx_documents_company_uploaded ON documents(company_id, uploaded_at);
CREATE INDEX idx_ocr_results_document ON ocr_results(document_id);
CREATE INDEX idx_ocr_results_company_status ON ocr_results(company_id, status);
CREATE INDEX idx_credit_ledger_company_created ON credit_ledger(company_id, created_at);

-- RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_ledger ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_tenant_policy ON documents USING (company_id = app.current_tenant());
CREATE POLICY ocr_results_tenant_policy ON ocr_results USING (company_id = app.current_tenant());
CREATE POLICY credit_ledger_tenant_policy ON credit_ledger USING (company_id = app.current_tenant());

-- Function to deduct credits
CREATE OR REPLACE FUNCTION app.deduct_credit(company_uuid UUID, amount NUMERIC(18,2), ref_type TEXT, ref_id UUID, desc_text TEXT, actor_uuid UUID) RETURNS VOID AS $$
DECLARE
    current_balance NUMERIC(18,2);
BEGIN
    SELECT credit_balance INTO current_balance FROM companies WHERE company_id = company_uuid;
    IF current_balance < amount THEN
        RAISE EXCEPTION 'Insufficient credits: required %, available %', amount, current_balance;
    END IF;

    UPDATE companies SET credit_balance = credit_balance - amount WHERE company_id = company_uuid;

    INSERT INTO credit_ledger (company_id, transaction_type, amount, balance_after, reference_type, reference_id, description, created_by)
    VALUES (company_uuid, 'deduction', -amount, current_balance - amount, ref_type, ref_id, desc_text, actor_uuid);
END;
$$ LANGUAGE plpgsql;

-- Function to add credits
CREATE OR REPLACE FUNCTION app.add_credit(company_uuid UUID, amount NUMERIC(18,2), txn_type credit_transaction_type_enum, ref_type TEXT, ref_id UUID, desc_text TEXT, actor_uuid UUID) RETURNS VOID AS $$
DECLARE
    new_balance NUMERIC(18,2);
BEGIN
    UPDATE companies SET credit_balance = credit_balance + amount WHERE company_id = company_uuid RETURNING credit_balance INTO new_balance;

    INSERT INTO credit_ledger (company_id, transaction_type, amount, balance_after, reference_type, reference_id, description, created_by)
    VALUES (company_uuid, txn_type, amount, new_balance, ref_type, ref_id, desc_text, actor_uuid);
END;
$$ LANGUAGE plpgsql;</content>
<parameter name="filePath">c:\Users\Milin\Desktop\OptiReach\optierp4\database\ocr_credit_schema.sql
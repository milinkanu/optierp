-- OCR and tenant credit schema additions.
-- Requires database/schema.sql. PostgreSQL 14+ compatible. Safe to run repeatedly.

DROP TABLE IF EXISTS credit_ledger CASCADE;
DROP TABLE IF EXISTS ocr_results CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TYPE IF EXISTS document_type_enum CASCADE;
DROP TYPE IF EXISTS credit_transaction_type_enum CASCADE;
DROP TYPE IF EXISTS ocr_mode_enum CASCADE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ocr_mode_enum') THEN
        CREATE TYPE ocr_mode_enum AS ENUM ('manual', 'ocr', 'smart');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'credit_transaction_type_enum') THEN
        CREATE TYPE credit_transaction_type_enum AS ENUM ('subscription', 'pay_as_you_go', 'bonus', 'deduction');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_type_enum') THEN
        CREATE TYPE document_type_enum AS ENUM ('invoice', 'receipt', 'bank_statement', 'kyc', 'other');
    END IF;
END$$;

ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS credit_balance NUMERIC(18,2) NOT NULL DEFAULT 0;

CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    document_type document_type_enum NOT NULL,
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_size BIGINT NOT NULL CHECK (file_size >= 0),
    mime_type TEXT NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES users(user_id),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    checksum TEXT NOT NULL
);

CREATE TABLE ocr_results (
    ocr_result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    mode ocr_mode_enum NOT NULL,
    paddleocr_confidence NUMERIC(5,4) CHECK (paddleocr_confidence IS NULL OR paddleocr_confidence BETWEEN 0 AND 1),
    vlm_confidence NUMERIC(5,4) CHECK (vlm_confidence IS NULL OR vlm_confidence BETWEEN 0 AND 1),
    extracted_data JSONB,
    ocr_metadata JSONB,
    status ocr_status_enum NOT NULL DEFAULT 'pending',
    processed_at TIMESTAMPTZ,
    confirmed_at TIMESTAMPTZ,
    confirmed_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE credit_ledger (
    credit_entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_type credit_transaction_type_enum NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    balance_after NUMERIC(18,2) NOT NULL,
    reference_type TEXT,
    reference_id UUID,
    description TEXT,
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_documents_company_uploaded ON documents(company_id, uploaded_at);
CREATE INDEX idx_ocr_results_document ON ocr_results(document_id);
CREATE INDEX idx_ocr_results_company_status ON ocr_results(company_id, status);
CREATE INDEX idx_credit_ledger_company_created ON credit_ledger(company_id, created_at);

CREATE OR REPLACE FUNCTION app.deduct_credit(
    company_uuid UUID,
    amount NUMERIC(18,2),
    ref_type TEXT,
    ref_id UUID,
    desc_text TEXT,
    actor_uuid UUID
) RETURNS VOID AS $$
DECLARE
    current_balance NUMERIC(18,2);
BEGIN
    IF amount <= 0 THEN
        RAISE EXCEPTION 'Credit deduction amount must be positive';
    END IF;

    SELECT credit_balance
      INTO current_balance
      FROM companies
     WHERE company_id = company_uuid
     FOR UPDATE;

    IF current_balance IS NULL THEN
        RAISE EXCEPTION 'Company % does not exist', company_uuid;
    END IF;
    IF current_balance < amount THEN
        RAISE EXCEPTION 'Insufficient credits: required %, available %', amount, current_balance;
    END IF;

    UPDATE companies
       SET credit_balance = credit_balance - amount
     WHERE company_id = company_uuid;

    INSERT INTO credit_ledger (company_id, transaction_type, amount, balance_after, reference_type, reference_id, description, created_by)
    VALUES (company_uuid, 'deduction', -amount, current_balance - amount, ref_type, ref_id, desc_text, actor_uuid);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.add_credit(
    company_uuid UUID,
    amount NUMERIC(18,2),
    txn_type credit_transaction_type_enum,
    ref_type TEXT,
    ref_id UUID,
    desc_text TEXT,
    actor_uuid UUID
) RETURNS VOID AS $$
DECLARE
    new_balance NUMERIC(18,2);
BEGIN
    IF amount <= 0 THEN
        RAISE EXCEPTION 'Credit amount must be positive';
    END IF;

    UPDATE companies
       SET credit_balance = credit_balance + amount
     WHERE company_id = company_uuid
     RETURNING credit_balance INTO new_balance;

    IF new_balance IS NULL THEN
        RAISE EXCEPTION 'Company % does not exist', company_uuid;
    END IF;

    INSERT INTO credit_ledger (company_id, transaction_type, amount, balance_after, reference_type, reference_id, description, created_by)
    VALUES (company_uuid, txn_type, amount, new_balance, ref_type, ref_id, desc_text, actor_uuid);
END;
$$ LANGUAGE plpgsql;

ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_ledger ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_tenant_policy ON documents USING (company_id = app.current_tenant());
CREATE POLICY ocr_results_tenant_policy ON ocr_results USING (company_id = app.current_tenant());
CREATE POLICY credit_ledger_tenant_policy ON credit_ledger USING (company_id = app.current_tenant());

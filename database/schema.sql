-- Core PostgreSQL schema for the FinOps Financial Operating System

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enums
CREATE TYPE company_type_enum AS ENUM ('sole_prop','partnership','pvt_ltd','llp','opc','HUF');
CREATE TYPE gst_type_enum AS ENUM ('regular','composition','unregistered','sez');
CREATE TYPE party_type_enum AS ENUM ('customer','vendor','employee','other');
CREATE TYPE txn_type_enum AS ENUM ('sales_invoice','purchase_invoice','payment','receipt','expense','journal','contra','debit_note','credit_note','purchase_order');
CREATE TYPE txn_status_enum AS ENUM ('draft','posted','partial','paid','overdue','cancelled','reversed');
CREATE TYPE ledger_entry_type_enum AS ENUM ('debit','credit','reversal');
CREATE TYPE import_source_enum AS ENUM ('pdf_upload','csv_upload','xls_upload','bank_api','netbanking_scrape');
CREATE TYPE import_status_enum AS ENUM ('processing','completed','failed');
CREATE TYPE ocr_status_enum AS ENUM ('pending','scanned','confirmed','failed');
CREATE TYPE gst_return_type_enum AS ENUM ('gstr1','gstr3b','gstr9','gstr9c');
CREATE TYPE filing_status_enum AS ENUM ('not_started','generated','filed','filed_with_late_fee');
CREATE TYPE outbox_status_enum AS ENUM ('pending','sent','failed','dead_letter');
CREATE TYPE account_type_enum AS ENUM ('asset','liability','equity','income','expense');
CREATE TYPE party_contact_type_enum AS ENUM ('billing','shipping');
CREATE TYPE kyc_document_type_enum AS ENUM ('gst_certificate','pan_card','udyam_certificate','mca_certificate','bank_proof');
CREATE TYPE onboarding_status_enum AS ENUM ('draft','api_prefilled','ocr_pending','ocr_completed','confirmed','completed','failed');
CREATE TYPE onboarding_job_status_enum AS ENUM ('pending','processing','completed','failed');

-- Tenant helper
CREATE SCHEMA IF NOT EXISTS app;

CREATE OR REPLACE FUNCTION app.current_tenant() RETURNS uuid AS $$
BEGIN
    RETURN current_setting('app.current_company', true)::uuid;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION app.get_effective_roles(user_uuid UUID) RETURNS TABLE(role_name TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT r.name
    FROM user_roles ur
    JOIN roles r ON ur.role_id = r.role_id
    WHERE ur.user_id = user_uuid
    UNION
    SELECT r.name
    FROM delegations d
    JOIN roles r ON d.role_id = r.role_id
    WHERE d.delegate_user_id = user_uuid
      AND d.is_active = TRUE
      AND now() BETWEEN d.start_date AND d.end_date;
END;
$$ LANGUAGE plpgsql STABLE;

-- Tables
CREATE TABLE companies (
    company_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    trade_name TEXT,
    company_type company_type_enum NOT NULL,
    pan TEXT NOT NULL CHECK (pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]{1}$'),
    gstin TEXT UNIQUE CHECK (gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    tan TEXT,
    udyam_no TEXT,
    gst_type gst_type_enum NOT NULL,
    primary_state TEXT NOT NULL,
    extra_states TEXT[],
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    user_version INTEGER NOT NULL DEFAULT 1, -- Increment on role/delegation changes to invalidate tokens
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, email)
);

CREATE TABLE roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, name)
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(user_id),
    role_id UUID NOT NULL REFERENCES roles(role_id),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(user_id, role_id)
);

CREATE TABLE permissions (
    permission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(role_id),
    permission TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(role_id, permission)
);

CREATE TABLE delegations (
    delegation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    delegator_user_id UUID NOT NULL REFERENCES users(user_id),
    delegate_user_id UUID NOT NULL REFERENCES users(user_id),
    role_id UUID NOT NULL REFERENCES roles(role_id),
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (start_date < end_date),
    CHECK (delegator_user_id != delegate_user_id),
    UNIQUE(delegator_user_id, delegate_user_id, role_id, start_date)
);

CREATE TABLE chart_of_accounts (
    account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    account_code TEXT NOT NULL,
    account_name TEXT NOT NULL,
    account_type account_type_enum NOT NULL,
    parent_account_id UUID REFERENCES chart_of_accounts(account_id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, account_code)
);

CREATE TYPE journal_type_enum AS ENUM ('adjustment','opening','closing','accrual','payment','receipt','reversal','misc');
CREATE TYPE journal_status_enum AS ENUM ('draft','posted','reversed','cancelled');

CREATE TABLE journal_entries (
    journal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    journal_number TEXT NOT NULL,
    journal_type journal_type_enum NOT NULL DEFAULT 'misc',
    journal_date DATE NOT NULL,
    description TEXT,
    reference TEXT,
    transaction_id UUID REFERENCES transactions(transaction_id),
    status journal_status_enum NOT NULL DEFAULT 'draft',
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, journal_number)
);

CREATE TABLE journal_entry_lines (
    journal_line_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id UUID NOT NULL REFERENCES journal_entries(journal_id) ON DELETE CASCADE,
    company_id UUID NOT NULL,
    account_id UUID NOT NULL REFERENCES chart_of_accounts(account_id),
    entry_type ledger_entry_type_enum NOT NULL CHECK (entry_type IN ('debit','credit')),
    amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    description TEXT,
    party_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_journal_entries_company_date ON journal_entries(company_id, journal_date);
CREATE INDEX idx_journal_entry_lines_company_journal ON journal_entry_lines(company_id, journal_id);
CREATE INDEX idx_journal_entry_lines_company_account ON journal_entry_lines(company_id, account_id);

CREATE TABLE bank_accounts (
    bank_account_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    account_number TEXT NOT NULL,
    ifsc_code TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    branch TEXT,
    currency TEXT NOT NULL DEFAULT 'INR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, account_number)
);

CREATE TABLE parties (
    party_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    party_name TEXT NOT NULL,
    party_type party_type_enum NOT NULL,
    gstin TEXT,
    billing_address JSONB,
    shipping_address JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, party_name)
);

CREATE TABLE transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    txn_type txn_type_enum NOT NULL,
    txn_number TEXT NOT NULL,
    txn_date DATE NOT NULL,
    fiscal_year TEXT NOT NULL,
    period TEXT NOT NULL,
    party_id UUID REFERENCES parties(party_id),
    subtotal NUMERIC(18,2) NOT NULL,
    gst_breakdown JSONB NOT NULL,
    grand_total NUMERIC(18,2) NOT NULL,
    status txn_status_enum NOT NULL DEFAULT 'draft',
    meta JSONB,
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, txn_type, txn_number)
);

CREATE INDEX idx_transactions_company_date_status ON transactions(company_id, txn_date, status);

CREATE TABLE transaction_items (
    transaction_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    company_id UUID NOT NULL,
    account_id UUID NOT NULL REFERENCES chart_of_accounts(account_id),
    description TEXT,
    quantity NUMERIC(18,4) DEFAULT 0,
    unit_price NUMERIC(18,4) DEFAULT 0,
    taxable_amount NUMERIC(18,2) NOT NULL,
    tax_rate NUMERIC(5,2) NOT NULL,
    tax_amount NUMERIC(18,2) NOT NULL,
    total_amount NUMERIC(18,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ledger_entries (
    ledger_entry_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    journal_id UUID REFERENCES journal_entries(journal_id),
    entry_type ledger_entry_type_enum NOT NULL,
    account_id UUID NOT NULL REFERENCES chart_of_accounts(account_id),
    amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    entry_date DATE NOT NULL,
    reference TEXT,
    party_id UUID,
    reversal_of UUID REFERENCES ledger_entries(ledger_entry_id),
    is_reversal BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID NOT NULL REFERENCES users(user_id),
    meta JSONB,
    CHECK ((entry_type = 'reversal') = is_reversal)
);

CREATE INDEX idx_ledger_company_transaction ON ledger_entries(company_id, transaction_id);
CREATE INDEX idx_ledger_company_date ON ledger_entries(company_id, entry_date);
CREATE INDEX idx_ledger_company_account_date ON ledger_entries(company_id, account_id, entry_date);

CREATE OR REPLACE FUNCTION app.ensure_journal_balance(journal_uuid UUID) RETURNS VOID AS $$
DECLARE
    total_debit NUMERIC(18,2);
    total_credit NUMERIC(18,2);
    journal_status journal_status_enum;
BEGIN
    SELECT status INTO journal_status FROM journal_entries WHERE journal_id = journal_uuid;
    IF journal_status IS NULL THEN
        RAISE EXCEPTION 'Journal entry % does not exist', journal_uuid;
    END IF;
    IF journal_status <> 'posted' THEN
        RETURN;
    END IF;

    SELECT COALESCE(SUM(CASE WHEN entry_type = 'debit' THEN amount ELSE 0 END), 0),
           COALESCE(SUM(CASE WHEN entry_type = 'credit' THEN amount ELSE 0 END), 0)
      INTO total_debit, total_credit
      FROM journal_entry_lines
     WHERE journal_id = journal_uuid;

    IF total_debit = 0 OR total_credit = 0 THEN
        RAISE EXCEPTION 'Journal entry % must contain both debit and credit lines', journal_uuid;
    END IF;
    IF total_debit <> total_credit THEN
        RAISE EXCEPTION 'Journal entry % is not balanced: debit % <> credit %', journal_uuid, total_debit, total_credit;
    END IF;
END;
$$ LANGUAGE plpgsql VOLATILE;

CREATE OR REPLACE FUNCTION app.validate_journal_line_company_consistency() RETURNS TRIGGER AS $$
DECLARE
    expected_company UUID;
    account_company UUID;
    current_company UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN
        current_company := OLD.company_id;
        SELECT company_id INTO expected_company FROM journal_entries WHERE journal_id = OLD.journal_id;
        SELECT company_id INTO account_company FROM chart_of_accounts WHERE account_id = OLD.account_id;
    ELSE
        current_company := NEW.company_id;
        SELECT company_id INTO expected_company FROM journal_entries WHERE journal_id = NEW.journal_id;
        SELECT company_id INTO account_company FROM chart_of_accounts WHERE account_id = NEW.account_id;
    END IF;

    IF expected_company IS NULL THEN
        RAISE EXCEPTION 'Journal entry % does not exist', COALESCE(NEW.journal_id, OLD.journal_id);
    END IF;
    IF account_company IS DISTINCT FROM expected_company THEN
        RAISE EXCEPTION 'Journal line account must belong to journal company %', expected_company;
    END IF;
    IF current_company IS DISTINCT FROM expected_company THEN
        RAISE EXCEPTION 'Journal line company_id must match journal company_id %', expected_company;
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.journal_balance_trigger() RETURNS TRIGGER AS $$
DECLARE
    journal_uuid UUID;
BEGIN
    IF TG_OP = 'DELETE' THEN
        journal_uuid := OLD.journal_id;
    ELSE
        journal_uuid := NEW.journal_id;
    END IF;
    PERFORM app.ensure_journal_balance(journal_uuid);
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.journal_status_trigger() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'posted' THEN
        PERFORM app.ensure_journal_balance(NEW.journal_id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_journal_line_company_consistency
BEFORE INSERT OR UPDATE OR DELETE ON journal_entry_lines
FOR EACH ROW EXECUTE FUNCTION app.validate_journal_line_company_consistency();

CREATE TRIGGER trg_journal_line_balance
AFTER INSERT OR UPDATE OR DELETE ON journal_entry_lines
FOR EACH ROW EXECUTE FUNCTION app.journal_balance_trigger();

CREATE TRIGGER trg_journal_status_balance
BEFORE INSERT OR UPDATE ON journal_entries
FOR EACH ROW EXECUTE FUNCTION app.journal_status_trigger();

CREATE OR REPLACE FUNCTION app.prevent_ledger_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Ledger entries are immutable. Updates and deletes are forbidden.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ledger_entries_immutable
BEFORE UPDATE OR DELETE ON ledger_entries
FOR EACH ROW EXECUTE FUNCTION app.prevent_ledger_mutation();

-- Tenant isolation policies for accounting tables
ALTER TABLE chart_of_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY chart_of_accounts_tenant_policy ON chart_of_accounts USING (company_id = app.current_tenant());

ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY journal_entries_tenant_policy ON journal_entries USING (company_id = app.current_tenant());

ALTER TABLE journal_entry_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY journal_entry_lines_tenant_policy ON journal_entry_lines USING (company_id = app.current_tenant());

ALTER TABLE ledger_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY ledger_entries_tenant_policy ON ledger_entries USING (company_id = app.current_tenant());

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_tenant_policy ON users USING (company_id = app.current_tenant());

ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY roles_tenant_policy ON roles USING (company_id = app.current_tenant());

ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_roles_tenant_policy ON user_roles USING (
    EXISTS (SELECT 1 FROM users u WHERE u.user_id = user_roles.user_id AND u.company_id = app.current_tenant())
);

ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY permissions_tenant_policy ON permissions USING (
    EXISTS (SELECT 1 FROM roles r WHERE r.role_id = permissions.role_id AND r.company_id = app.current_tenant())
);

ALTER TABLE delegations ENABLE ROW LEVEL SECURITY;
CREATE POLICY delegations_tenant_policy ON delegations USING (company_id = app.current_tenant());

CREATE TABLE referral_schemes (
    scheme_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    scheme_name TEXT NOT NULL,
    scheme_type TEXT NOT NULL,
    calculation_base TEXT NOT NULL,
    rate NUMERIC(10,4),
    slab_config JSONB,
    min_invoice_value NUMERIC(18,2),
    applicable_on TEXT NOT NULL,
    payout_trigger TEXT NOT NULL,
    payout_frequency TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ocr_documents (
    ocr_document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID REFERENCES transactions(transaction_id),
    source_type TEXT NOT NULL,
    source_reference TEXT,
    confidence NUMERIC(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    extracted_data JSONB,
    ocr_metadata JSONB,
    status ocr_status_enum NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at TIMESTAMPTZ,
    confirmed_by UUID REFERENCES users(user_id)
);

CREATE TABLE kyc_documents (
    kyc_document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    document_type kyc_document_type_enum NOT NULL,
    document_url TEXT NOT NULL, -- Object storage URL
    extracted_data JSONB,
    ocr_metadata JSONB,
    confidence NUMERIC(5,4) CHECK (confidence >= 0 AND confidence <= 1),
    status ocr_status_enum NOT NULL DEFAULT 'pending',
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at TIMESTAMPTZ,
    confirmed_by UUID REFERENCES users(user_id)
);

CREATE TABLE onboarding_jobs (
    onboarding_job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    job_type TEXT NOT NULL, -- 'api_prefill' or 'ocr_extraction'
    status onboarding_job_status_enum NOT NULL DEFAULT 'pending',
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE e_invoices (
    e_invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    irn TEXT,
    ack_no TEXT,
    qr_code TEXT,
    eway_bill_no TEXT,
    generated_at TIMESTAMPTZ,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bank_statements (
    bank_statement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    bank_account_id UUID NOT NULL REFERENCES bank_accounts(bank_account_id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    opening_balance NUMERIC(18,2) NOT NULL,
    closing_balance NUMERIC(18,2) NOT NULL,
    import_source import_source_enum NOT NULL,
    total_txn_count INT,
    import_status import_status_enum NOT NULL,
    import_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bank_transactions (
    bank_transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bank_statement_id UUID NOT NULL REFERENCES bank_statements(bank_statement_id) ON DELETE CASCADE,
    company_id UUID NOT NULL,
    transaction_date DATE NOT NULL,
    amount NUMERIC(18,2) NOT NULL,
    credit_debit TEXT NOT NULL,
    utr TEXT,
    narration TEXT,
    matched BOOLEAN NOT NULL DEFAULT FALSE,
    matched_transaction_id UUID REFERENCES transactions(transaction_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_bank_txn_company_date_amount ON bank_transactions(company_id, transaction_date, amount);

CREATE TABLE gst_returns (
    gst_return_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    return_type gst_return_type_enum NOT NULL,
    period TEXT NOT NULL,
    filing_status filing_status_enum NOT NULL,
    return_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE itr_computations (
    itr_computation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    financial_year TEXT NOT NULL,
    gross_receipts NUMERIC(18,2),
    total_expenses NUMERIC(18,2),
    net_profit NUMERIC(18,2),
    disallowed_expenses NUMERIC(18,2),
    taxable_income NUMERIC(18,2),
    presumptive_income NUMERIC(18,2),
    depreciation_total NUMERIC(18,2),
    schedule_mapping JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE inventory_items (
    inventory_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    hsn_sac TEXT,
    unit TEXT NOT NULL,
    valuation_method TEXT NOT NULL,
    opening_stock NUMERIC(18,4),
    opening_value NUMERIC(18,2),
    gst_rate NUMERIC(5,2),
    godown_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, item_name)
);

CREATE TABLE audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    entity_name TEXT NOT NULL,
    entity_id UUID NOT NULL,
    operation TEXT NOT NULL,
    actor_id UUID NOT NULL,
    before_state JSONB,
    after_state JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    record_hash TEXT NOT NULL,
    previous_hash TEXT
);

CREATE TABLE outbox (
    outbox_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    status outbox_status_enum NOT NULL DEFAULT 'pending',
    attempt_count INT NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_attempt_at TIMESTAMPTZ
);

CREATE TABLE api_idempotency_keys (
    idempotency_key UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    user_id UUID NOT NULL,
    endpoint TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    UNIQUE(company_id, endpoint, request_hash)
);

-- Audit hash chain trigger
CREATE OR REPLACE FUNCTION app.audit_log_hash_trigger() RETURNS trigger AS $$
DECLARE
    prior_hash TEXT;
BEGIN
    SELECT record_hash INTO prior_hash
      FROM audit_logs
     WHERE entity_name = NEW.entity_name
       AND entity_id = NEW.entity_id
     ORDER BY created_at DESC
     LIMIT 1;
    NEW.previous_hash := prior_hash;
    NEW.record_hash := encode(digest(coalesce(prior_hash, '') || coalesce(NEW.operation, '') || coalesce(NEW.actor_id::text, '') || coalesce(NEW.created_at::text, '') || coalesce(NEW.after_state::text, ''), 'sha256'), 'hex');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_hash BEFORE INSERT ON audit_logs
FOR EACH ROW EXECUTE FUNCTION app.audit_log_hash_trigger();

-- Ledger immutability enforcement
CREATE OR REPLACE FUNCTION app.ledger_entry_immutability() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Ledger entries are immutable. Use reversal entries instead.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ledger_entries_immutability
    BEFORE UPDATE OR DELETE ON ledger_entries
    FOR EACH ROW EXECUTE FUNCTION app.ledger_entry_immutability();

-- Tenant row level security
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chart_of_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transaction_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE referral_schemes ENABLE ROW LEVEL SECURITY;
ALTER TABLE ocr_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE kyc_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE onboarding_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE e_invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE bank_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE gst_returns ENABLE ROW LEVEL SECURITY;
ALTER TABLE itr_computations ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_idempotency_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_companies ON companies
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_default ON users
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_roles ON roles
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_user_roles ON user_roles
    USING (user_id IN (SELECT user_id FROM users WHERE company_id = app.current_tenant()));

CREATE POLICY tenant_isolation_permissions ON permissions
    USING (role_id IN (SELECT role_id FROM roles WHERE company_id = app.current_tenant()));

CREATE POLICY tenant_isolation_chart_of_accounts ON chart_of_accounts
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_bank_accounts ON bank_accounts
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_parties ON parties
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_transactions ON transactions
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_transaction_items ON transaction_items
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_ledger_entries ON ledger_entries
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_referral_schemes ON referral_schemes
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_ocr_documents ON ocr_documents
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_kyc_documents ON kyc_documents
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_onboarding_jobs ON onboarding_jobs
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_e_invoices ON e_invoices
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_bank_statements ON bank_statements
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_bank_transactions ON bank_transactions
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_gst_returns ON gst_returns
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_itr_computations ON itr_computations
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_inventory_items ON inventory_items
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_audit_logs ON audit_logs
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_outbox ON outbox
    USING (company_id = app.current_tenant());

CREATE POLICY tenant_isolation_idempotency ON api_idempotency_keys
    USING (company_id = app.current_tenant());

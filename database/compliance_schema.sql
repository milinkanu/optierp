-- Compliance engine schema for GST, TDS, TCS, and advance tax.
-- Requires database/schema.sql. PostgreSQL 14+ compatible. Safe to run repeatedly.

DROP TABLE IF EXISTS tax_reconciliations CASCADE;
DROP TABLE IF EXISTS compliance_thresholds CASCADE;
DROP TABLE IF EXISTS advance_tax_payments CASCADE;
DROP TABLE IF EXISTS advance_tax_liability CASCADE;
DROP TABLE IF EXISTS tcs_returns CASCADE;
DROP TABLE IF EXISTS tcs_collections CASCADE;
DROP TABLE IF EXISTS tds_returns CASCADE;
DROP TABLE IF EXISTS tds_deductions CASCADE;
DROP TABLE IF EXISTS gst_return_items CASCADE;
DROP TABLE IF EXISTS gst_returns CASCADE;
DROP TABLE IF EXISTS gst_liability CASCADE;
DROP TABLE IF EXISTS tax_rules CASCADE;
DROP TABLE IF EXISTS tax_rates CASCADE;

DROP TYPE IF EXISTS gst_return_status_enum CASCADE;
DROP TYPE IF EXISTS filing_frequency_enum CASCADE;
DROP TYPE IF EXISTS compliance_status_enum CASCADE;
DROP TYPE IF EXISTS tcs_section_enum CASCADE;
DROP TYPE IF EXISTS tds_section_enum CASCADE;
DROP TYPE IF EXISTS gst_component_enum CASCADE;
DROP TYPE IF EXISTS tax_type_enum CASCADE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tax_type_enum') THEN
        CREATE TYPE tax_type_enum AS ENUM ('gst', 'tds', 'tcs', 'advance_tax');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'gst_component_enum') THEN
        CREATE TYPE gst_component_enum AS ENUM ('cgst', 'sgst', 'igst', 'cess');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tds_section_enum') THEN
        CREATE TYPE tds_section_enum AS ENUM ('192', '192A', '193', '194', '194A', '194B', '194BB', '194C', '194D', '194DA', '194E', '194EE', '194F', '194G', '194H', '194I', '194IA', '194IB', '194IC', '194J', '194K', '194LA', '194LB', '194LC', '194LD', '195', '196A', '196B', '196C', '196D', '197', '198', '199', '200', '201', '202', '203');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tcs_section_enum') THEN
        CREATE TYPE tcs_section_enum AS ENUM ('195', '196C');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'compliance_status_enum') THEN
        CREATE TYPE compliance_status_enum AS ENUM ('pending', 'calculated', 'filed', 'overdue', 'amended');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'filing_frequency_enum') THEN
        CREATE TYPE filing_frequency_enum AS ENUM ('monthly', 'quarterly', 'annual');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'gst_return_status_enum') THEN
        CREATE TYPE gst_return_status_enum AS ENUM ('not_started', 'generated', 'filed', 'filed_late', 'amended', 'cancelled');
    END IF;
END$$;

CREATE TABLE tax_rates (
    tax_rate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    tax_type tax_type_enum NOT NULL,
    section_code TEXT,
    hsn_sac_code TEXT,
    rate NUMERIC(5,2) NOT NULL CHECK (rate >= 0 AND rate <= 100),
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, tax_type, section_code, hsn_sac_code, effective_from)
);

CREATE TABLE tax_rules (
    tax_rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    rule_name TEXT NOT NULL,
    tax_type tax_type_enum NOT NULL,
    condition_json JSONB NOT NULL,
    action_json JSONB NOT NULL,
    priority INT NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, rule_name)
);

CREATE TABLE gst_liability (
    gst_liability_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    invoice_id UUID,
    gstin TEXT NOT NULL CHECK (gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    component gst_component_enum NOT NULL,
    taxable_amount NUMERIC(18,2) NOT NULL CHECK (taxable_amount >= 0),
    rate NUMERIC(5,2) NOT NULL CHECK (rate >= 0 AND rate <= 100),
    amount NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
    period TEXT NOT NULL,
    is_input BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, transaction_id, component)
);

CREATE TABLE gst_returns (
    gst_return_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    return_type TEXT NOT NULL CHECK (return_type IN ('GSTR1', 'GSTR3B', 'GSTR9', 'GSTR9C')),
    period TEXT NOT NULL,
    filing_date DATE,
    due_date DATE NOT NULL,
    status gst_return_status_enum NOT NULL DEFAULT 'not_started',
    total_taxable_value NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_tax_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    json_data JSONB,
    ack_no TEXT,
    arn TEXT,
    error_messages TEXT[],
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, return_type, period)
);

CREATE TABLE gst_return_items (
    gst_return_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gst_return_id UUID NOT NULL REFERENCES gst_returns(gst_return_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    invoice_id UUID,
    gstin TEXT CHECK (gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    component gst_component_enum NOT NULL,
    taxable_value NUMERIC(18,2) NOT NULL CHECK (taxable_value >= 0),
    tax_amount NUMERIC(18,2) NOT NULL CHECK (tax_amount >= 0),
    hsn_sac TEXT,
    rate NUMERIC(5,2) NOT NULL CHECK (rate >= 0 AND rate <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tds_deductions (
    tds_deduction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    payment_id UUID REFERENCES transactions(transaction_id),
    section tds_section_enum NOT NULL,
    deductee_name TEXT NOT NULL,
    deductee_pan TEXT NOT NULL CHECK (deductee_pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]{1}$'),
    deductee_gstin TEXT CHECK (deductee_gstin IS NULL OR deductee_gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    payment_amount NUMERIC(18,2) NOT NULL CHECK (payment_amount > 0),
    tds_rate NUMERIC(5,2) NOT NULL CHECK (tds_rate >= 0 AND tds_rate <= 100),
    tds_amount NUMERIC(18,2) NOT NULL CHECK (tds_amount >= 0),
    surcharge NUMERIC(18,2) NOT NULL DEFAULT 0,
    cess NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_tax NUMERIC(18,2) NOT NULL CHECK (total_tax >= 0),
    period TEXT NOT NULL,
    challan_no TEXT,
    challan_date DATE,
    deposited BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, transaction_id, section)
);

CREATE TABLE tds_returns (
    tds_return_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    form_no TEXT NOT NULL CHECK (form_no IN ('24Q', '26Q', '27Q', '27EQ')),
    period TEXT NOT NULL,
    filing_date DATE,
    due_date DATE NOT NULL,
    status compliance_status_enum NOT NULL DEFAULT 'pending',
    total_deductions NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_deposits NUMERIC(18,2) NOT NULL DEFAULT 0,
    json_data JSONB,
    token_no TEXT,
    error_messages TEXT[],
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, form_no, period)
);

CREATE TABLE tcs_collections (
    tcs_collection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    receipt_id UUID REFERENCES transactions(transaction_id),
    section tcs_section_enum NOT NULL,
    collectee_name TEXT NOT NULL,
    collectee_pan TEXT NOT NULL CHECK (collectee_pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]{1}$'),
    collectee_gstin TEXT CHECK (collectee_gstin IS NULL OR collectee_gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    receipt_amount NUMERIC(18,2) NOT NULL CHECK (receipt_amount > 0),
    tcs_rate NUMERIC(5,2) NOT NULL CHECK (tcs_rate >= 0 AND tcs_rate <= 100),
    tcs_amount NUMERIC(18,2) NOT NULL CHECK (tcs_amount >= 0),
    surcharge NUMERIC(18,2) NOT NULL DEFAULT 0,
    cess NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_tax NUMERIC(18,2) NOT NULL CHECK (total_tax >= 0),
    period TEXT NOT NULL,
    challan_no TEXT,
    challan_date DATE,
    deposited BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, transaction_id, section)
);

CREATE TABLE tcs_returns (
    tcs_return_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    form_no TEXT NOT NULL CHECK (form_no IN ('27EQ')),
    period TEXT NOT NULL,
    filing_date DATE,
    due_date DATE NOT NULL,
    status compliance_status_enum NOT NULL DEFAULT 'pending',
    total_collections NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_deposits NUMERIC(18,2) NOT NULL DEFAULT 0,
    json_data JSONB,
    token_no TEXT,
    error_messages TEXT[],
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, form_no, period)
);

CREATE TABLE advance_tax_liability (
    advance_tax_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    assessment_year TEXT NOT NULL,
    quarter TEXT NOT NULL CHECK (quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    estimated_income NUMERIC(18,2) NOT NULL CHECK (estimated_income >= 0),
    tax_rate NUMERIC(5,2) NOT NULL CHECK (tax_rate >= 0 AND tax_rate <= 100),
    advance_tax_due NUMERIC(18,2) NOT NULL CHECK (advance_tax_due >= 0),
    surcharge NUMERIC(18,2) NOT NULL DEFAULT 0,
    cess NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_tax NUMERIC(18,2) NOT NULL CHECK (total_tax >= 0),
    due_date DATE NOT NULL,
    paid_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
    balance NUMERIC(18,2) GENERATED ALWAYS AS (total_tax - paid_amount) STORED,
    status compliance_status_enum NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, assessment_year, quarter)
);

CREATE TABLE advance_tax_payments (
    advance_tax_payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advance_tax_id UUID NOT NULL REFERENCES advance_tax_liability(advance_tax_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    payment_date DATE NOT NULL,
    amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    challan_no TEXT NOT NULL,
    bsr_code TEXT NOT NULL,
    mode_of_payment TEXT NOT NULL CHECK (mode_of_payment IN ('cash', 'cheque', 'online')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(challan_no, bsr_code)
);

CREATE TABLE compliance_thresholds (
    threshold_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    tax_type tax_type_enum NOT NULL,
    threshold_type TEXT NOT NULL,
    threshold_value NUMERIC(18,2) NOT NULL CHECK (threshold_value >= 0),
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, tax_type, threshold_type, effective_from)
);

CREATE TABLE tax_reconciliations (
    reconciliation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    tax_type tax_type_enum NOT NULL,
    period TEXT NOT NULL,
    book_tax_difference NUMERIC(18,2) NOT NULL DEFAULT 0,
    adjustments JSONB,
    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
    reconciled_by UUID REFERENCES users(user_id),
    reconciled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_gst_liability_company_period ON gst_liability(company_id, period);
CREATE INDEX idx_gst_liability_transaction ON gst_liability(transaction_id);
CREATE INDEX idx_gst_returns_company_period ON gst_returns(company_id, period);
CREATE INDEX idx_tds_deductions_company_period ON tds_deductions(company_id, period);
CREATE INDEX idx_tds_returns_company_period ON tds_returns(company_id, period);
CREATE INDEX idx_tcs_collections_company_period ON tcs_collections(company_id, period);
CREATE INDEX idx_advance_tax_company_year ON advance_tax_liability(company_id, assessment_year);

DO $$
BEGIN
    IF to_regclass('public.invoices') IS NOT NULL THEN
        ALTER TABLE gst_liability
            ADD CONSTRAINT gst_liability_invoice_fk
            FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id);

        ALTER TABLE gst_return_items
            ADD CONSTRAINT gst_return_items_invoice_fk
            FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id);
    END IF;
END$$;

ALTER TABLE tax_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE gst_liability ENABLE ROW LEVEL SECURITY;
ALTER TABLE gst_returns ENABLE ROW LEVEL SECURITY;
ALTER TABLE gst_return_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE tds_deductions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tds_returns ENABLE ROW LEVEL SECURITY;
ALTER TABLE tcs_collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE tcs_returns ENABLE ROW LEVEL SECURITY;
ALTER TABLE advance_tax_liability ENABLE ROW LEVEL SECURITY;
ALTER TABLE advance_tax_payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_thresholds ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_reconciliations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tax_rates_isolation ON tax_rates USING (company_id = app.current_tenant());
CREATE POLICY tax_rules_isolation ON tax_rules USING (company_id = app.current_tenant());
CREATE POLICY gst_liability_isolation ON gst_liability USING (company_id = app.current_tenant());
CREATE POLICY gst_returns_isolation ON gst_returns USING (company_id = app.current_tenant());
CREATE POLICY gst_return_items_isolation ON gst_return_items USING (company_id = app.current_tenant());
CREATE POLICY tds_deductions_isolation ON tds_deductions USING (company_id = app.current_tenant());
CREATE POLICY tds_returns_isolation ON tds_returns USING (company_id = app.current_tenant());
CREATE POLICY tcs_collections_isolation ON tcs_collections USING (company_id = app.current_tenant());
CREATE POLICY tcs_returns_isolation ON tcs_returns USING (company_id = app.current_tenant());
CREATE POLICY advance_tax_isolation ON advance_tax_liability USING (company_id = app.current_tenant());
CREATE POLICY advance_tax_payments_isolation ON advance_tax_payments USING (company_id = app.current_tenant());
CREATE POLICY thresholds_isolation ON compliance_thresholds USING (company_id = app.current_tenant());
CREATE POLICY reconciliations_isolation ON tax_reconciliations USING (company_id = app.current_tenant());

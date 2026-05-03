-- Compliance Engine Schema for GST, TDS, TCS, and Advance Tax
-- Extends the core FinOps schema with tax compliance features

-- Enums for compliance
CREATE TYPE IF NOT EXISTS tax_type_enum AS ENUM ('gst', 'tds', 'tcs', 'advance_tax');
CREATE TYPE IF NOT EXISTS gst_component_enum AS ENUM ('cgst', 'sgst', 'igst', 'cess');
CREATE TYPE IF NOT EXISTS tds_section_enum AS ENUM ('192', '192A', '193', '194', '194A', '194B', '194BB', '194C', '194D', '194DA', '194E', '194EE', '194F', '194G', '194H', '194I', '194IA', '194IB', '194IC', '194J', '194K', '194LA', '194LB', '194LC', '194LD', '195', '196A', '196B', '196C', '196D', '197', '198', '199', '200', '201', '202', '203');
CREATE TYPE IF NOT EXISTS tcs_section_enum AS ENUM ('195', '196C');
CREATE TYPE IF NOT EXISTS compliance_status_enum AS ENUM ('pending', 'calculated', 'filed', 'overdue', 'amended');
CREATE TYPE IF NOT EXISTS filing_frequency_enum AS ENUM ('monthly', 'quarterly', 'annual');
CREATE TYPE IF NOT EXISTS gst_return_status_enum AS ENUM ('not_started', 'generated', 'filed', 'filed_late', 'amended', 'cancelled');

-- Tax Configuration Tables
CREATE TABLE IF NOT EXISTS tax_rates (
    tax_rate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    tax_type tax_type_enum NOT NULL,
    section_code TEXT, -- TDS/TCS section or GST type
    hsn_sac_code TEXT, -- For GST
    rate NUMERIC(5,2) NOT NULL CHECK (rate >= 0 AND rate <= 100),
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, tax_type, section_code, hsn_sac_code, effective_from)
);

CREATE TABLE IF NOT EXISTS tax_rules (
    tax_rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    rule_name TEXT NOT NULL,
    tax_type tax_type_enum NOT NULL,
    condition_json JSONB NOT NULL, -- Rule conditions in JSON
    action_json JSONB NOT NULL, -- Actions to take when condition matches
    priority INT NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, rule_name)
);

-- GST Compliance Tables
CREATE TABLE IF NOT EXISTS gst_liability (
    gst_liability_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    invoice_id UUID REFERENCES invoices(invoice_id),
    gstin TEXT NOT NULL CHECK (gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    component gst_component_enum NOT NULL,
    taxable_amount NUMERIC(18,2) NOT NULL CHECK (taxable_amount >= 0),
    rate NUMERIC(5,2) NOT NULL CHECK (rate >= 0 AND rate <= 100),
    amount NUMERIC(18,2) NOT NULL CHECK (amount >= 0),
    period TEXT NOT NULL, -- YYYY-MM
    is_input BOOLEAN NOT NULL DEFAULT FALSE, -- TRUE for purchases, FALSE for sales
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, transaction_id, component)
);

CREATE TABLE IF NOT EXISTS gst_returns (
    gst_return_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    return_type TEXT NOT NULL CHECK (return_type IN ('GSTR1', 'GSTR3B', 'GSTR9', 'GSTR9C')),
    period TEXT NOT NULL, -- YYYY-MM for monthly, YYYY-Q1 etc for quarterly
    filing_date DATE,
    due_date DATE NOT NULL,
    status gst_return_status_enum NOT NULL DEFAULT 'not_started',
    total_taxable_value NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_tax_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    json_data JSONB, -- Complete return data
    ack_no TEXT,
    arn TEXT,
    error_messages TEXT[],
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, return_type, period)
);

CREATE TABLE IF NOT EXISTS gst_return_items (
    gst_return_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gst_return_id UUID NOT NULL REFERENCES gst_returns(gst_return_id) ON DELETE CASCADE,
    company_id UUID NOT NULL,
    invoice_id UUID REFERENCES invoices(invoice_id),
    gstin TEXT,
    component gst_component_enum NOT NULL,
    taxable_value NUMERIC(18,2) NOT NULL,
    tax_amount NUMERIC(18,2) NOT NULL,
    hsn_sac TEXT,
    rate NUMERIC(5,2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TDS Compliance Tables
CREATE TABLE IF NOT EXISTS tds_deductions (
    tds_deduction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    payment_id UUID REFERENCES transactions(transaction_id), -- Link to payment transaction
    section tds_section_enum NOT NULL,
    deductee_name TEXT NOT NULL,
    deductee_pan TEXT NOT NULL CHECK (deductee_pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]{1}$'),
    deductee_gstin TEXT CHECK (deductee_gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    payment_amount NUMERIC(18,2) NOT NULL CHECK (payment_amount > 0),
    tds_rate NUMERIC(5,2) NOT NULL CHECK (tds_rate >= 0 AND tds_rate <= 100),
    tds_amount NUMERIC(18,2) NOT NULL CHECK (tds_amount >= 0),
    surcharge NUMERIC(18,2) NOT NULL DEFAULT 0,
    cess NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_tax NUMERIC(18,2) NOT NULL,
    period TEXT NOT NULL, -- YYYY-Q1, YYYY-Q2, etc.
    challan_no TEXT,
    challan_date DATE,
    deposited BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, transaction_id, section)
);

CREATE TABLE IF NOT EXISTS tds_returns (
    tds_return_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    form_no TEXT NOT NULL CHECK (form_no IN ('24Q', '26Q', '27Q', '27EQ')),
    period TEXT NOT NULL, -- YYYY-Q1, YYYY-Q2, etc.
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

-- TCS Compliance Tables
CREATE TABLE IF NOT EXISTS tcs_collections (
    tcs_collection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id),
    receipt_id UUID REFERENCES transactions(transaction_id),
    section tcs_section_enum NOT NULL,
    collectee_name TEXT NOT NULL,
    collectee_pan TEXT NOT NULL CHECK (collectee_pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]{1}$'),
    collectee_gstin TEXT CHECK (collectee_gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'),
    receipt_amount NUMERIC(18,2) NOT NULL CHECK (receipt_amount > 0),
    tcs_rate NUMERIC(5,2) NOT NULL CHECK (tcs_rate >= 0 AND tcs_rate <= 100),
    tcs_amount NUMERIC(18,2) NOT NULL CHECK (tcs_amount >= 0),
    surcharge NUMERIC(18,2) NOT NULL DEFAULT 0,
    cess NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_tax NUMERIC(18,2) NOT NULL,
    period TEXT NOT NULL,
    challan_no TEXT,
    challan_date DATE,
    deposited BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, transaction_id, section)
);

CREATE TABLE IF NOT EXISTS tcs_returns (
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

-- Advance Tax Tables
CREATE TABLE IF NOT EXISTS advance_tax_liability (
    advance_tax_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    assessment_year TEXT NOT NULL, -- YYYY-YY format
    quarter TEXT NOT NULL CHECK (quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    estimated_income NUMERIC(18,2) NOT NULL CHECK (estimated_income >= 0),
    tax_rate NUMERIC(5,2) NOT NULL CHECK (tax_rate >= 0 AND tax_rate <= 100),
    advance_tax_due NUMERIC(18,2) NOT NULL CHECK (advance_tax_due >= 0),
    surcharge NUMERIC(18,2) NOT NULL DEFAULT 0,
    cess NUMERIC(18,2) NOT NULL DEFAULT 0,
    total_tax NUMERIC(18,2) NOT NULL,
    due_date DATE NOT NULL,
    paid_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
    balance NUMERIC(18,2) GENERATED ALWAYS AS (total_tax - paid_amount) STORED,
    status compliance_status_enum NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, assessment_year, quarter)
);

CREATE TABLE IF NOT EXISTS advance_tax_payments (
    advance_tax_payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advance_tax_id UUID NOT NULL REFERENCES advance_tax_liability(advance_tax_id),
    company_id UUID NOT NULL,
    payment_date DATE NOT NULL,
    amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    challan_no TEXT NOT NULL,
    bsr_code TEXT NOT NULL,
    mode_of_payment TEXT NOT NULL CHECK (mode_of_payment IN ('cash', 'cheque', 'online')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(challan_no, bsr_code)
);

-- Threshold and Compliance Settings
CREATE TABLE IF NOT EXISTS compliance_thresholds (
    threshold_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    tax_type tax_type_enum NOT NULL,
    threshold_type TEXT NOT NULL, -- 'turnover', 'transaction_value', 'annual_income', etc.
    threshold_value NUMERIC(18,2) NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, tax_type, threshold_type, effective_from)
);

-- Audit and Reconciliation
CREATE TABLE IF NOT EXISTS tax_reconciliations (
    reconciliation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    tax_type tax_type_enum NOT NULL,
    period TEXT NOT NULL,
    book_tax_difference NUMERIC(18,2) NOT NULL DEFAULT 0,
    adjustments JSONB, -- Details of adjustments made
    reconciled BOOLEAN NOT NULL DEFAULT FALSE,
    reconciled_by UUID REFERENCES users(user_id),
    reconciled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_gst_liability_company_period ON gst_liability(company_id, period);
CREATE INDEX IF NOT EXISTS idx_gst_liability_transaction ON gst_liability(transaction_id);
CREATE INDEX IF NOT EXISTS idx_gst_returns_company_period ON gst_returns(company_id, period);
CREATE INDEX IF NOT EXISTS idx_tds_deductions_company_period ON tds_deductions(company_id, period);
CREATE INDEX IF NOT EXISTS idx_tds_returns_company_period ON tds_returns(company_id, period);
CREATE INDEX IF NOT EXISTS idx_tcs_collections_company_period ON tcs_collections(company_id, period);
CREATE INDEX IF NOT EXISTS idx_advance_tax_company_year ON advance_tax_liability(company_id, assessment_year);

-- Row Level Security
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

-- RLS Policies (assuming app.current_tenant() function exists)
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
CREATE POLICY reconciliations_isolation ON tax_reconciliations USING (company_id = app.current_tenant());</content>
<parameter name="filePath">c:\Users\Milin\Desktop\OptiReach\optierp4\database\compliance_schema.sql
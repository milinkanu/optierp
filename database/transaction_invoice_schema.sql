-- Transaction and invoice schema additions for the OptiReach FinOps platform.
-- Requires database/schema.sql. PostgreSQL 14+ compatible. Safe to run repeatedly.

DROP TRIGGER IF EXISTS trg_transactions_posted_outbox ON transactions;
DROP TABLE IF EXISTS invoice_payment_allocations CASCADE;
DROP TABLE IF EXISTS invoice_items CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS invoice_series CASCADE;
DROP TYPE IF EXISTS invoice_status_enum CASCADE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'invoice_status_enum') THEN
        CREATE TYPE invoice_status_enum AS ENUM ('draft','posted','partial','paid','overdue','cancelled','reversed');
    END IF;
END$$;

ALTER TYPE txn_type_enum ADD VALUE IF NOT EXISTS 'payment_inbound';
ALTER TYPE txn_type_enum ADD VALUE IF NOT EXISTS 'payment_outbound';

ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'INR',
    ADD COLUMN IF NOT EXISTS exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS settlement_bank_account_id UUID REFERENCES bank_accounts(bank_account_id),
    ADD COLUMN IF NOT EXISTS idempotency_key UUID;

CREATE TABLE invoice_series (
    invoice_series_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    invoice_type txn_type_enum NOT NULL CHECK (invoice_type IN ('sales_invoice','purchase_invoice')),
    prefix TEXT NOT NULL DEFAULT 'INV',
    last_sequence BIGINT NOT NULL DEFAULT 0,
    format_pattern TEXT NOT NULL DEFAULT 'INV-{YYYY}-{seq:06}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, invoice_type)
);

CREATE TABLE invoices (
    invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    transaction_id UUID NOT NULL UNIQUE REFERENCES transactions(transaction_id),
    invoice_number TEXT NOT NULL,
    invoice_type txn_type_enum NOT NULL CHECK (invoice_type IN ('sales_invoice','purchase_invoice')),
    invoice_date DATE NOT NULL,
    due_date DATE,
    billing_party_id UUID NOT NULL REFERENCES parties(party_id),
    shipping_party_id UUID REFERENCES parties(party_id),
    currency TEXT NOT NULL DEFAULT 'INR',
    exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
    invoice_subtotal NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (invoice_subtotal >= 0),
    invoice_total_gst NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (invoice_total_gst >= 0),
    invoice_total_tds NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (invoice_total_tds >= 0),
    invoice_total_tcs NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (invoice_total_tcs >= 0),
    invoice_grand_total NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (invoice_grand_total >= 0),
    paid_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
    balance_due NUMERIC(18,2) GENERATED ALWAYS AS (invoice_grand_total - paid_amount) STORED,
    status invoice_status_enum NOT NULL DEFAULT 'draft',
    meta JSONB,
    created_by UUID NOT NULL REFERENCES users(user_id),
    updated_by UUID NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(company_id, invoice_type, invoice_number)
);

CREATE TABLE invoice_items (
    invoice_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    line_number INT NOT NULL,
    description TEXT NOT NULL,
    hsn_sac TEXT NOT NULL CHECK (hsn_sac ~ '^[0-9A-Z]{4,8}$'),
    inventory_item_id UUID REFERENCES inventory_items(inventory_item_id),
    account_id UUID NOT NULL REFERENCES chart_of_accounts(account_id),
    quantity NUMERIC(18,4) NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(18,4) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    taxable_amount NUMERIC(18,2) NOT NULL CHECK (taxable_amount >= 0),
    gst_rate NUMERIC(5,2) NOT NULL CHECK (gst_rate >= 0 AND gst_rate <= 100),
    gst_amount NUMERIC(18,2) NOT NULL CHECK (gst_amount >= 0),
    tds_rate NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (tds_rate >= 0 AND tds_rate <= 100),
    tds_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (tds_amount >= 0),
    tcs_rate NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (tcs_rate >= 0 AND tcs_rate <= 100),
    tcs_amount NUMERIC(18,2) NOT NULL DEFAULT 0 CHECK (tcs_amount >= 0),
    total_amount NUMERIC(18,2) NOT NULL CHECK (total_amount >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(invoice_id, line_number)
);

CREATE TABLE invoice_payment_allocations (
    allocation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    payment_transaction_id UUID NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,
    invoice_id UUID NOT NULL REFERENCES invoices(invoice_id) ON DELETE CASCADE,
    allocated_amount NUMERIC(18,2) NOT NULL CHECK (allocated_amount > 0),
    currency TEXT NOT NULL DEFAULT 'INR',
    exchange_rate NUMERIC(18,8) NOT NULL DEFAULT 1,
    allocated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(payment_transaction_id, invoice_id)
);

CREATE INDEX idx_invoice_series_company_type ON invoice_series(company_id, invoice_type);
CREATE INDEX idx_invoices_company_status_due ON invoices(company_id, status, due_date);
CREATE INDEX idx_invoice_items_company_invoice ON invoice_items(company_id, invoice_id);
CREATE INDEX idx_invoice_allocations_company_invoice ON invoice_payment_allocations(company_id, invoice_id);

CREATE OR REPLACE FUNCTION app.next_invoice_number(p_company_id uuid, p_invoice_type txn_type_enum) RETURNS text AS $$
DECLARE
    series_row invoice_series%ROWTYPE;
    next_seq BIGINT;
    year_text TEXT := to_char(now(), 'YYYY');
BEGIN
    SELECT * INTO series_row
      FROM invoice_series
     WHERE company_id = p_company_id
       AND invoice_type = p_invoice_type
     FOR UPDATE;

    IF NOT FOUND THEN
        INSERT INTO invoice_series(company_id, invoice_type, prefix, last_sequence, format_pattern)
        VALUES (p_company_id, p_invoice_type, upper(p_invoice_type::text), 0, 'INV-' || year_text || '-{seq:06}')
        RETURNING * INTO series_row;
    END IF;

    next_seq := series_row.last_sequence + 1;
    UPDATE invoice_series
       SET last_sequence = next_seq,
           updated_at = now()
     WHERE invoice_series_id = series_row.invoice_series_id;

    RETURN series_row.prefix || '-' || year_text || '-' || lpad(next_seq::text, 6, '0');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.recalculate_invoice_totals() RETURNS trigger AS $$
DECLARE
    totals RECORD;
    target_invoice_id UUID := COALESCE(NEW.invoice_id, OLD.invoice_id);
BEGIN
    SELECT
        COALESCE(SUM(taxable_amount), 0) AS subtotal,
        COALESCE(SUM(gst_amount), 0) AS gst_total,
        COALESCE(SUM(tds_amount), 0) AS tds_total,
        COALESCE(SUM(tcs_amount), 0) AS tcs_total,
        COALESCE(SUM(total_amount), 0) AS grand_total
      INTO totals
      FROM invoice_items
     WHERE invoice_id = target_invoice_id;

    UPDATE invoices
       SET invoice_subtotal = totals.subtotal,
           invoice_total_gst = totals.gst_total,
           invoice_total_tds = totals.tds_total,
           invoice_total_tcs = totals.tcs_total,
           invoice_grand_total = totals.grand_total,
           updated_at = now()
     WHERE invoice_id = target_invoice_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.update_invoice_payment_balance() RETURNS trigger AS $$
DECLARE
    total_paid NUMERIC(18,2);
    target_invoice_id UUID := COALESCE(NEW.invoice_id, OLD.invoice_id);
BEGIN
    SELECT COALESCE(SUM(allocated_amount), 0) INTO total_paid
      FROM invoice_payment_allocations
     WHERE invoice_id = target_invoice_id;

    UPDATE invoices
       SET paid_amount = total_paid,
           status = CASE
               WHEN total_paid >= invoice_grand_total AND invoice_grand_total > 0 THEN 'paid'
               WHEN total_paid > 0 AND total_paid < invoice_grand_total THEN 'partial'
               ELSE status
           END,
           updated_at = now()
     WHERE invoice_id = target_invoice_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION app.enqueue_outbox_event() RETURNS trigger AS $$
DECLARE
    aggregate_uuid UUID;
BEGIN
    IF TG_TABLE_NAME = 'invoices' THEN
        aggregate_uuid := NEW.invoice_id;
    ELSIF TG_TABLE_NAME = 'transactions' THEN
        aggregate_uuid := NEW.transaction_id;
    ELSE
        RAISE EXCEPTION 'Unsupported outbox source table: %', TG_TABLE_NAME;
    END IF;

    INSERT INTO outbox (company_id, aggregate_type, aggregate_id, event_type, payload, status, created_at)
    VALUES (
        NEW.company_id,
        TG_TABLE_NAME,
        aggregate_uuid,
        TG_ARGV[0],
        jsonb_build_object(
            'company_id', NEW.company_id,
            'aggregate_id', aggregate_uuid,
            'source', TG_TABLE_NAME,
            'new_state', to_jsonb(NEW)
        ),
        'pending',
        now()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_invoice_items_recalculate
AFTER INSERT OR UPDATE OR DELETE ON invoice_items
FOR EACH ROW EXECUTE FUNCTION app.recalculate_invoice_totals();

CREATE TRIGGER trg_invoice_payment_allocations_update
AFTER INSERT OR UPDATE OR DELETE ON invoice_payment_allocations
FOR EACH ROW EXECUTE FUNCTION app.update_invoice_payment_balance();

CREATE TRIGGER trg_invoices_posted_outbox
AFTER INSERT OR UPDATE OF status ON invoices
FOR EACH ROW WHEN (NEW.status = 'posted')
EXECUTE FUNCTION app.enqueue_outbox_event('invoice.posted');

CREATE TRIGGER trg_transactions_posted_outbox
AFTER INSERT OR UPDATE OF status ON transactions
FOR EACH ROW WHEN (NEW.status IN ('posted','paid','partial'))
EXECUTE FUNCTION app.enqueue_outbox_event('transaction.posted');

ALTER TABLE invoice_series ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_payment_allocations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_invoice_series ON invoice_series USING (company_id = app.current_tenant());
CREATE POLICY tenant_isolation_invoices ON invoices USING (company_id = app.current_tenant());
CREATE POLICY tenant_isolation_invoice_items ON invoice_items USING (company_id = app.current_tenant());
CREATE POLICY tenant_isolation_invoice_payment_allocations ON invoice_payment_allocations USING (company_id = app.current_tenant());

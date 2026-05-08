-- Compliance engine seed data.
-- Requires database/schema.sql and database/compliance_schema.sql.
-- Safe to run repeatedly. Inserts are skipped when no company/user seed exists.

WITH seed_company AS (
    SELECT company_id
      FROM companies
     ORDER BY created_at
     LIMIT 1
)
INSERT INTO tax_rates (company_id, tax_type, section_code, hsn_sac_code, rate, effective_from)
SELECT company_id, tax_type::tax_type_enum, section_code, hsn_sac_code, rate, effective_from::date
  FROM seed_company
 CROSS JOIN (
    VALUES
        ('gst', NULL, '998311', 18.0, '2023-01-01'),
        ('gst', NULL, '997212', 18.0, '2023-01-01'),
        ('gst', NULL, '995411', 18.0, '2023-01-01'),
        ('tds', '194C', NULL, 1.0, '2023-01-01'),
        ('tds', '194J', NULL, 10.0, '2023-01-01'),
        ('tds', '194I', NULL, 10.0, '2023-01-01'),
        ('tds', '194IA', NULL, 1.0, '2023-01-01'),
        ('tcs', '195', NULL, 1.0, '2023-01-01'),
        ('tcs', '196C', NULL, 1.0, '2023-01-01')
 ) AS rows(tax_type, section_code, hsn_sac_code, rate, effective_from)
 WHERE NOT EXISTS (
    SELECT 1
      FROM tax_rates tr
     WHERE tr.company_id = seed_company.company_id
       AND tr.tax_type = rows.tax_type::tax_type_enum
       AND tr.section_code IS NOT DISTINCT FROM rows.section_code
       AND tr.hsn_sac_code IS NOT DISTINCT FROM rows.hsn_sac_code
       AND tr.effective_from = rows.effective_from::date
 );

WITH seed_company AS (
    SELECT company_id
      FROM companies
     ORDER BY created_at
     LIMIT 1
)
INSERT INTO tax_rules (company_id, rule_name, tax_type, condition_json, action_json, priority)
SELECT company_id, rule_name, tax_type::tax_type_enum, condition_json::jsonb, action_json::jsonb, priority
  FROM seed_company
 CROSS JOIN (
    VALUES
        ('GST on Sales Invoice', 'gst', '{"txn_type": "sales_invoice"}', '{"calculate_gst": true}', 1),
        ('GST on Purchase Invoice', 'gst', '{"txn_type": "purchase_invoice"}', '{"calculate_gst": true, "input_credit": true}', 1),
        ('TDS on Contractor Payment', 'tds', '{"txn_type": "payment", "party_type": "vendor", "payment_type": "contract"}', '{"section": "194C"}', 1),
        ('TDS on Professional Fees', 'tds', '{"txn_type": "payment", "party_type": "vendor", "payment_type": "professional"}', '{"section": "194J"}', 1),
        ('TDS on Rent', 'tds', '{"txn_type": "payment", "party_type": "vendor", "payment_type": "rent"}', '{"section": "194I"}', 1),
        ('TCS on Foreign Remittance', 'tcs', '{"txn_type": "payment", "currency": "USD"}', '{"section": "195"}', 1)
 ) AS rows(rule_name, tax_type, condition_json, action_json, priority)
ON CONFLICT (company_id, rule_name) DO NOTHING;

WITH seed_company AS (
    SELECT company_id
      FROM companies
     ORDER BY created_at
     LIMIT 1
)
INSERT INTO compliance_thresholds (company_id, tax_type, threshold_type, threshold_value, effective_from)
SELECT company_id, tax_type::tax_type_enum, threshold_type, threshold_value, effective_from::date
  FROM seed_company
 CROSS JOIN (
    VALUES
        ('gst', 'turnover', 4000000.00, '2023-01-01'),
        ('tds', 'annual_turnover', 50000000.00, '2023-01-01'),
        ('advance_tax', 'annual_income', 10000000.00, '2023-01-01')
 ) AS rows(tax_type, threshold_type, threshold_value, effective_from)
ON CONFLICT (company_id, tax_type, threshold_type, effective_from) DO NOTHING;

WITH seed_company AS (
    SELECT company_id
      FROM companies
     ORDER BY created_at
     LIMIT 1
)
INSERT INTO advance_tax_liability (
    company_id,
    assessment_year,
    quarter,
    estimated_income,
    tax_rate,
    advance_tax_due,
    surcharge,
    cess,
    total_tax,
    due_date
)
SELECT company_id, assessment_year, quarter, estimated_income, tax_rate, advance_tax_due, surcharge, cess, total_tax, due_date::date
  FROM seed_company
 CROSS JOIN (
    VALUES
        ('2024-25', 'Q1', 5000000.00, 20.0, 1000000.00, 0.00, 4000.00, 1004000.00, '2024-07-31'),
        ('2024-25', 'Q2', 5000000.00, 20.0, 1000000.00, 0.00, 4000.00, 1004000.00, '2024-10-31'),
        ('2024-25', 'Q3', 5000000.00, 20.0, 1000000.00, 0.00, 4000.00, 1004000.00, '2025-01-31'),
        ('2024-25', 'Q4', 5000000.00, 20.0, 1000000.00, 0.00, 4000.00, 1004000.00, '2025-03-31')
 ) AS rows(assessment_year, quarter, estimated_income, tax_rate, advance_tax_due, surcharge, cess, total_tax, due_date)
ON CONFLICT (company_id, assessment_year, quarter) DO NOTHING;

WITH seed AS (
    SELECT c.company_id, u.user_id
      FROM companies c
      JOIN users u ON u.company_id = c.company_id
     ORDER BY c.created_at, u.created_at
     LIMIT 1
)
INSERT INTO gst_returns (
    company_id,
    return_type,
    period,
    due_date,
    total_taxable_value,
    total_tax_amount,
    status,
    created_by,
    updated_by
)
SELECT company_id, return_type, period, due_date::date, total_taxable_value, total_tax_amount, 'generated'::gst_return_status_enum, user_id, user_id
  FROM seed
 CROSS JOIN (
    VALUES
        ('GSTR1', '2024-04', '2024-05-11', 500000.00, 90000.00),
        ('GSTR3B', '2024-04', '2024-05-20', 500000.00, 90000.00)
 ) AS rows(return_type, period, due_date, total_taxable_value, total_tax_amount)
ON CONFLICT (company_id, return_type, period) DO NOTHING;

WITH seed AS (
    SELECT c.company_id, u.user_id
      FROM companies c
      JOIN users u ON u.company_id = c.company_id
     ORDER BY c.created_at, u.created_at
     LIMIT 1
)
INSERT INTO tds_returns (
    company_id,
    form_no,
    period,
    due_date,
    total_deductions,
    total_deposits,
    status,
    created_by,
    updated_by
)
SELECT company_id, '24Q', '2024-Q1', '2024-10-31'::date, 25000.00, 25000.00, 'calculated'::compliance_status_enum, user_id, user_id
  FROM seed
ON CONFLICT (company_id, form_no, period) DO NOTHING;

WITH seed AS (
    SELECT c.company_id, u.user_id
      FROM companies c
      JOIN users u ON u.company_id = c.company_id
     ORDER BY c.created_at, u.created_at
     LIMIT 1
)
INSERT INTO tcs_returns (
    company_id,
    form_no,
    period,
    due_date,
    total_collections,
    total_deposits,
    status,
    created_by,
    updated_by
)
SELECT company_id, '27EQ', '2024-Q1', '2024-10-31'::date, 5000.00, 5000.00, 'calculated'::compliance_status_enum, user_id, user_id
  FROM seed
ON CONFLICT (company_id, form_no, period) DO NOTHING;

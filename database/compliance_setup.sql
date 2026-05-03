-- Compliance Engine Setup Script
-- Sample data and rules for GST, TDS, TCS, and Advance Tax compliance

-- Insert sample tax rates (these should be customized per company)
INSERT INTO tax_rates (company_id, tax_type, section_code, hsn_sac_code, rate, effective_from) VALUES
-- GST Rates
((SELECT company_id FROM companies LIMIT 1), 'gst', NULL, '998311', 18.0, '2023-01-01'), -- IT services
((SELECT company_id FROM companies LIMIT 1), 'gst', NULL, '997212', 18.0, '2023-01-01'), -- Consulting services
((SELECT company_id FROM companies LIMIT 1), 'gst', NULL, '995411', 18.0, '2023-01-01'), -- Construction services
-- TDS Rates
((SELECT company_id FROM companies LIMIT 1), 'tds', '194C', NULL, 1.0, '2023-01-01'), -- Payment to contractors
((SELECT company_id FROM companies LIMIT 1), 'tds', '194J', NULL, 10.0, '2023-01-01'), -- Professional fees
((SELECT company_id FROM companies LIMIT 1), 'tds', '194I', NULL, 10.0, '2023-01-01'), -- Rent
((SELECT company_id FROM companies LIMIT 1), 'tds', '194IA', NULL, 1.0, '2023-01-01'), -- Property purchase
-- TCS Rates
((SELECT company_id FROM companies LIMIT 1), 'tcs', '195', NULL, 1.0, '2023-01-01'), -- Foreign remittance
((SELECT company_id FROM companies LIMIT 1), 'tcs', '196C', NULL, 1.0, '2023-01-01'); -- T-Bills

-- Insert sample tax rules
INSERT INTO tax_rules (company_id, rule_name, tax_type, condition_json, action_json, priority) VALUES
-- GST Rules
((SELECT company_id FROM companies LIMIT 1), 'GST on Sales Invoice', 'gst',
 '{"txn_type": "sales_invoice"}',
 '{"calculate_gst": true}',
 1),
((SELECT company_id FROM companies LIMIT 1), 'GST on Purchase Invoice', 'gst',
 '{"txn_type": "purchase_invoice"}',
 '{"calculate_gst": true, "input_credit": true}',
 1),
-- TDS Rules
((SELECT company_id FROM companies LIMIT 1), 'TDS on Contractor Payment', 'tds',
 '{"txn_type": "payment", "party_type": "vendor", "payment_type": "contract"}',
 '{"section": "194C"}',
 1),
((SELECT company_id FROM companies LIMIT 1), 'TDS on Professional Fees', 'tds',
 '{"txn_type": "payment", "party_type": "vendor", "payment_type": "professional"}',
 '{"section": "194J"}',
 1),
((SELECT company_id FROM companies LIMIT 1), 'TDS on Rent', 'tds',
 '{"txn_type": "payment", "party_type": "vendor", "payment_type": "rent"}',
 '{"section": "194I"}',
 1),
-- TCS Rules
((SELECT company_id FROM companies LIMIT 1), 'TCS on Foreign Remittance', 'tcs',
 '{"txn_type": "payment", "currency": "USD"}',
 '{"section": "195"}',
 1);

-- Insert compliance thresholds
INSERT INTO compliance_thresholds (company_id, tax_type, threshold_type, threshold_value, effective_from) VALUES
((SELECT company_id FROM companies LIMIT 1), 'gst', 'turnover', 4000000.00, '2023-01-01'), -- ₹40 lakhs GST threshold
((SELECT company_id FROM companies LIMIT 1), 'tds', 'annual_turnover', 50000000.00, '2023-01-01'), -- ₹5 crores TDS threshold
((SELECT company_id FROM companies LIMIT 1), 'advance_tax', 'annual_income', 10000000.00, '2023-01-01'); -- ₹1 crore advance tax threshold

-- Sample advance tax liability (for demonstration)
INSERT INTO advance_tax_liability (company_id, assessment_year, quarter, estimated_income, tax_rate, advance_tax_due, surcharge, cess, total_tax, due_date) VALUES
((SELECT company_id FROM companies LIMIT 1), '2024-25', 'Q1', 5000000.00, 20.0, 1000000.00, 0.00, 4000.00, 1004000.00, '2024-07-31'),
((SELECT company_id FROM companies LIMIT 1), '2024-25', 'Q2', 5000000.00, 20.0, 1000000.00, 0.00, 4000.00, 1004000.00, '2024-10-31'),
((SELECT company_id FROM companies LIMIT 1), '2024-25', 'Q3', 5000000.00, 20.0, 1000000.00, 0.00, 4000.00, 1004000.00, '2025-01-31'),
((SELECT company_id FROM companies LIMIT 1), '2024-25', 'Q4', 5000000.00, 20.0, 1000000.00, 0.00, 4000.00, 1004000.00, '2025-03-31');

-- Sample GST return (for demonstration)
INSERT INTO gst_returns (company_id, return_type, period, due_date, total_taxable_value, total_tax_amount, status, created_by, updated_by) VALUES
((SELECT company_id FROM companies LIMIT 1), 'GSTR1', '2024-04', '2024-05-11', 500000.00, 90000.00, 'generated',
 (SELECT user_id FROM users LIMIT 1), (SELECT user_id FROM users LIMIT 1)),
((SELECT company_id FROM companies LIMIT 1), 'GSTR3B', '2024-04', '2024-05-20', 500000.00, 90000.00, 'generated',
 (SELECT user_id FROM users LIMIT 1), (SELECT user_id FROM users LIMIT 1));

-- Sample TDS return (for demonstration)
INSERT INTO tds_returns (company_id, form_no, period, due_date, total_deductions, total_deposits, status, created_by, updated_by) VALUES
((SELECT company_id FROM companies LIMIT 1), '24Q', '2024-Q1', '2024-10-31', 25000.00, 25000.00, 'generated',
 (SELECT user_id FROM users LIMIT 1), (SELECT user_id FROM users LIMIT 1));

-- Sample TCS return (for demonstration)
INSERT INTO tcs_returns (company_id, form_no, period, due_date, total_collections, total_deposits, status, created_by, updated_by) VALUES
((SELECT company_id FROM companies LIMIT 1), '27EQ', '2024-Q1', '2024-10-31', 5000.00, 5000.00, 'generated',
 (SELECT user_id FROM users LIMIT 1), (SELECT user_id FROM users LIMIT 1));</content>
<parameter name="filePath">c:\Users\Milin\Desktop\OptiReach\optierp4\database\compliance_setup.sql
# FinOps Compliance Engine

A comprehensive tax compliance engine for GST, TDS, TCS, and Advance Tax calculations with rule-based processing and automated reporting.

## Features

### Tax Types Supported
- **GST (Goods and Services Tax)**: CGST, SGST, IGST, CESS calculations
- **TDS (Tax Deducted at Source)**: All major sections (194C, 194J, 194I, etc.)
- **TCS (Tax Collected at Source)**: Foreign remittances, T-Bills
- **Advance Tax**: Quarterly liability calculation and tracking

### Key Capabilities
- **Auto-calculation**: Automatic tax computation from transactions
- **Rule-based Engine**: Configurable tax rules and conditions
- **Multi-tenant**: Company-level isolation and configuration
- **Threshold Monitoring**: Automatic breach detection
- **Return Generation**: Automated GST returns (GSTR1, GSTR3B, etc.)
- **Reconciliation**: Book vs actual tax payment matching
- **Edge Case Handling**: Threshold breaches, amendments, late filings

## Database Schema

### Core Tables
- `tax_rates`: Configurable tax rates by type, section, HSN/SAC
- `tax_rules`: Rule-based tax calculation logic
- `gst_liability`: GST liability tracking per transaction
- `gst_returns`: GST return filing records
- `tds_deductions`: TDS deduction records
- `tds_returns`: TDS return filing records
- `tcs_collections`: TCS collection records
- `tcs_returns`: TCS return filing records
- `advance_tax_liability`: Advance tax calculations
- `compliance_thresholds`: Threshold monitoring
- `tax_reconciliations`: Reconciliation tracking

## API Endpoints

### Configuration
```http
POST /compliance/tax-rates          # Configure tax rates
POST /compliance/tax-rules          # Configure tax rules
```

### GST Compliance
```http
POST /compliance/gst/calculate/{transaction_id}  # Calculate GST for transaction
POST /compliance/gst/returns                     # Generate GST return
GET  /compliance/gst/returns                     # List GST returns
```

### TDS Compliance
```http
POST /compliance/tds/calculate/{transaction_id}  # Calculate TDS for transaction
POST /compliance/tds/returns                     # Generate TDS return
```

### TCS Compliance
```http
POST /compliance/tcs/calculate/{transaction_id}  # Calculate TCS for transaction
POST /compliance/tcs/returns                     # Generate TCS return
```

### Advance Tax
```http
POST /compliance/advance-tax                     # Create advance tax liability
GET  /compliance/advance-tax                     # Get advance tax liabilities
```

### Reporting & Monitoring
```http
POST /compliance/reports                         # Generate compliance reports
GET  /compliance/thresholds/check                # Check threshold breaches
```

## Setup Instructions

1. **Apply Database Schema**:
   ```sql
   \i database/compliance_schema.sql
   ```

2. **Configure Sample Data**:
   ```sql
   \i database/compliance_setup.sql
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r services/requirements.txt
   ```

4. **Start Service**:
   ```bash
   uvicorn services.compliance_service:app --reload
   ```

## Configuration Examples

### GST Rate Configuration
```json
{
  "tax_type": "gst",
  "hsn_sac_code": "998311",
  "rate": 18.0,
  "effective_from": "2023-01-01"
}
```

### Tax Rule Configuration
```json
{
  "rule_name": "GST on Sales",
  "tax_type": "gst",
  "condition_json": {
    "txn_type": "sales_invoice"
  },
  "action_json": {
    "calculate_gst": true
  },
  "priority": 1
}
```

## Calculation Logic

### GST Calculation
- **Intra-state**: CGST + SGST (equal split)
- **Inter-state**: IGST (full rate)
- **Input Credit**: Automatic tracking for purchases
- **Reverse Charge**: Configurable based on rules

### TDS/TCS Rates
- Section-based rates (194C, 194J, etc.)
- Threshold-based variations
- Surcharge and cess calculations

### Advance Tax
- Income-based tax slabs
- Quarterly due dates
- Payment tracking and balance calculation

## Edge Cases Handled

### GST
- Composition scheme vs regular
- SEZ supplies
- Exempt supplies
- Reverse charge mechanism
- Input credit restrictions

### TDS/TCS
- Threshold breaches
- Lower/Nil deduction certificates
- Non-resident payments
- Section conflicts

### Advance Tax
- Estimated income revisions
- Interest calculations for late payments
- Carry forward balances

## Reports Generated

### GST Reports
- GSTR1: Outward supplies
- GSTR3B: Monthly summary
- GSTR9: Annual reconciliation
- GSTR9C: Reconciliation statement

### TDS/TCS Reports
- Form 24Q: Salary TDS
- Form 26Q: Non-salary TDS
- Form 27Q: Contractor TDS
- Form 27EQ: TCS

### Compliance Reports
- Liability summaries
- Payment reconciliation
- Threshold monitoring
- Due date tracking

## Integration Points

### Transaction Processing
- Automatic tax calculation on transaction creation
- Real-time compliance checks
- Audit trail maintenance

### Payment Processing
- TDS/TCS deduction at payment
- Challan tracking
- Deposit reconciliation

### Return Filing
- JSON data generation for GST portal
- Validation before filing
- Status tracking

## Security & Compliance

- **Row Level Security**: Company-based data isolation
- **Audit Logging**: All compliance actions tracked
- **Data Encryption**: Sensitive data (PAN, GSTIN) encrypted
- **Immutable Records**: Tax calculations cannot be modified
- **Validation**: GSTIN checksum, PAN format validation

## Performance Considerations

- **Indexing**: Optimized indexes on frequently queried columns
- **Partitioning**: Period-based partitioning for large datasets
- **Caching**: Tax rate caching for performance
- **Async Processing**: Background processing for bulk operations

## Monitoring & Alerts

- **Threshold Alerts**: Automatic notification of breaches
- **Due Date Tracking**: Upcoming filing deadline alerts
- **Reconciliation Alerts**: Book vs actual discrepancies
- **Compliance Score**: Overall compliance health metrics

## Future Enhancements

- Integration with GST/Tax portals
- Machine learning for tax optimization
- Multi-currency support
- International tax compliance
- Automated filing workflows</content>
<parameter name="filePath">c:\Users\Milin\Desktop\OptiReach\optierp4\COMPLIANCE_ENGINE_README.md
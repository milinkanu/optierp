from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Mapping, Optional, Union
from uuid import UUID, uuid4
import json
import re

from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.common import TenantContext, get_current_context, get_db

app = FastAPI(title='FinOps Compliance Service')

# Pydantic Models
class TaxRateConfig(BaseModel):
    tax_type: str = Field(..., pattern=r'^(gst|tds|tcs|advance_tax)$')
    section_code: Optional[str] = None
    hsn_sac_code: Optional[str] = None
    rate: float = Field(..., ge=0, le=100)
    effective_from: date
    effective_to: Optional[date] = None

class TaxRuleConfig(BaseModel):
    rule_name: str
    tax_type: str = Field(..., pattern=r'^(gst|tds|tcs|advance_tax)$')
    condition_json: Dict[str, Any]
    action_json: Dict[str, Any]
    priority: int = 1

class GSTLiability(BaseModel):
    gst_liability_id: UUID
    transaction_id: UUID
    gstin: str
    component: str = Field(..., pattern=r'^(cgst|sgst|igst|cess)$')
    taxable_amount: float
    rate: float
    amount: float
    period: str
    is_input: bool

class GSTReturnRequest(BaseModel):
    return_type: str = Field(..., pattern=r'^(GSTR1|GSTR3B|GSTR9|GSTR9C)$')
    period: str = Field(..., pattern=r'^\d{4}-(0[1-9]|1[0-2])$')

class GSTReturnResponse(BaseModel):
    gst_return_id: UUID
    return_type: str
    period: str
    status: str
    total_taxable_value: float
    total_tax_amount: float
    filing_date: Optional[date] = None
    due_date: date

class TDSDeduction(BaseModel):
    tds_deduction_id: UUID
    transaction_id: UUID
    section: str
    deductee_name: str
    deductee_pan: str
    payment_amount: float
    tds_rate: float
    tds_amount: float
    period: str

class TDSReturnRequest(BaseModel):
    form_no: str = Field(..., pattern=r'^(24Q|26Q|27Q|27EQ)$')
    period: str = Field(..., pattern=r'^\d{4}-Q[1-4]$')

class TCSCollection(BaseModel):
    tcs_collection_id: UUID
    transaction_id: UUID
    section: str
    collectee_name: str
    collectee_pan: str
    receipt_amount: float
    tcs_rate: float
    tcs_amount: float
    period: str = ''

class AdvanceTaxLiability(BaseModel):
    advance_tax_id: UUID
    assessment_year: str
    quarter: str
    estimated_income: float
    advance_tax_due: float
    total_tax: float
    due_date: date
    paid_amount: float
    balance: float
    status: str

class ComplianceReportRequest(BaseModel):
    report_type: str = Field(..., pattern=r'^(gst_liability|tds_summary|tcs_summary|advance_tax|reconciliation)$')
    period: str
    filters: Optional[Dict[str, Any]] = None

# Tax Calculation Engine
class TaxCalculator:
    @staticmethod
    def validate_gstin(gstin: str) -> bool:
        """Validate GSTIN format and checksum"""
        if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin):
            return False

        # GSTIN checksum validation
        weights = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1]
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        gstin_codes = []

        for char in gstin[:14]:
            if char.isdigit():
                gstin_codes.append(int(char))
            else:
                gstin_codes.append(ord(char) - ord('A') + 10)

        total = 0
        for i, code in enumerate(gstin_codes):
            product = code * weights[i]
            total += product // 36 + product % 36

        check_digit = (36 - (total % 36)) % 36
        expected_char = chars[check_digit]

        return gstin[14] == expected_char

    @staticmethod
    def calculate_gst_components(taxable_amount: float, gst_rate: float, state_of_supply: str, state_of_origin: str) -> Dict[str, float]:
        """Calculate CGST, SGST, IGST components"""
        if state_of_supply == state_of_origin:
            # Intra-state supply
            cgst_rate = gst_rate / 2
            sgst_rate = gst_rate / 2
            igst_rate = 0
        else:
            # Inter-state supply
            cgst_rate = 0
            sgst_rate = 0
            igst_rate = gst_rate

        return {
            'cgst_amount': round(taxable_amount * cgst_rate / 100, 2),
            'sgst_amount': round(taxable_amount * sgst_rate / 100, 2),
            'igst_amount': round(taxable_amount * igst_rate / 100, 2),
            'total_gst': round(taxable_amount * gst_rate / 100, 2)
        }

    @staticmethod
    def get_tds_rate(section: str, payment_amount: float, financial_year: str) -> float:
        """Get TDS rate based on section and payment amount"""
        # Simplified TDS rates - in production, this should be configurable
        tds_rates = {
            '194C': 1.0 if payment_amount <= 30000 else 2.0,  # Single payment threshold
            '194J': 10.0,
            '194I': 10.0,
            '194IA': 1.0,
            '194H': 5.0,
            '194A': 2.0 if payment_amount <= 50000 else 5.0,
        }
        return tds_rates.get(section, 0.0)

    @staticmethod
    def get_tcs_rate(section: str, receipt_amount: float) -> float:
        """Get TCS rate based on section and receipt amount"""
        tcs_rates = {
            '195': 1.0,  # Foreign remittance
            '196C': 1.0,  # Sale of T-Bills
        }
        return tcs_rates.get(section, 0.0)

    @staticmethod
    def calculate_advance_tax(estimated_income: float, assessment_year: str) -> Dict[str, Any]:
        """Calculate advance tax liability"""
        # Simplified tax slabs - should be configurable
        if estimated_income <= 250000:
            tax_rate = 0.0
        elif estimated_income <= 500000:
            tax_rate = 5.0
        elif estimated_income <= 1000000:
            tax_rate = 20.0
        else:
            tax_rate = 30.0

        tax_amount = estimated_income * tax_rate / 100
        surcharge = tax_amount * 0.10 if estimated_income > 5000000 else 0
        cess = (tax_amount + surcharge) * 0.04

        return {
            'tax_rate': tax_rate,
            'tax_amount': tax_amount,
            'surcharge': surcharge,
            'cess': cess,
            'total_tax': tax_amount + surcharge + cess
        }

    @staticmethod
    def evaluate_rule(condition: Dict[str, Any], data: Mapping[str, Any]) -> bool:
        """Evaluate rule condition against transaction data"""
        for key, expected in condition.items():
            if key not in data or data[key] != expected:
                return False
        return True

    @staticmethod
    def get_quarter(tx_date: date) -> str:
        """Get quarter string for given date"""
        year = tx_date.year
        quarter = (tx_date.month - 1) // 3 + 1
        return f"{year}-Q{quarter}"

# Database Operations
async def get_tax_rates(db: AsyncSession, company_id: UUID, tax_type: str, effective_date: date) -> List[Dict]:
    """Get applicable tax rates for given type and date"""
    query = text("""
        SELECT section_code, hsn_sac_code, rate
        FROM tax_rates
        WHERE company_id = :company_id
          AND tax_type = :tax_type
          AND effective_from <= :effective_date
          AND (effective_to IS NULL OR effective_to >= :effective_date)
          AND is_active = TRUE
        ORDER BY effective_from DESC
    """)

    result = await db.execute(query, {
        'company_id': company_id,
        'tax_type': tax_type,
        'effective_date': effective_date
    })

    return [dict(row) for row in result.mappings()]

async def get_tax_rules(db: AsyncSession, company_id: UUID, tax_type: str) -> List[Dict]:
    """Get active tax rules for given type"""
    query = text("""
        SELECT rule_name, condition_json, action_json, priority
        FROM tax_rules
        WHERE company_id = :company_id
          AND tax_type = :tax_type
          AND is_active = TRUE
        ORDER BY priority DESC
    """)

    result = await db.execute(query, {
        'company_id': company_id,
        'tax_type': tax_type
    })

    return [dict(row) for row in result.mappings()]

async def calculate_transaction_taxes(db: AsyncSession, company_id: UUID, transaction_id: UUID) -> Dict[str, Any]:
    """Calculate taxes for a transaction based on rules and rates"""
    # Get transaction details
    txn_query = text("""
        SELECT t.txn_type, t.txn_date, t.subtotal, t.gst_breakdown,
               p.gstin as party_gstin, p.party_type,
               c.gstin as company_gstin, c.primary_state, c.gst_type
        FROM transactions t
        JOIN parties p ON t.party_id = p.party_id
        JOIN companies c ON t.company_id = c.company_id
        WHERE t.transaction_id = :transaction_id AND t.company_id = :company_id
    """)

    txn_result = await db.execute(txn_query, {
        'transaction_id': transaction_id,
        'company_id': company_id
    })

    txn_data_row = txn_result.mappings().first()
    if not txn_data_row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn_data = dict(txn_data_row)

    taxes = {
        'gst': [],
        'tds': [],
        'tcs': [],
        'advance_tax': []
    }

    # GST Calculation
    if txn_data['gst_breakdown']:
        for component, details in txn_data['gst_breakdown'].items():
            gst_liability = {
                'component': component.lower(),
                'taxable_amount': details.get('taxable_amount', 0),
                'rate': details.get('rate', 0),
                'amount': details.get('amount', 0),
                'period': txn_data['txn_date'].strftime('%Y-%m'),
                'is_input': txn_data['txn_type'] in ['purchase_invoice']
            }
            taxes['gst'].append(gst_liability)

    # TDS Calculation for payments
    if txn_data['txn_type'] in ['payment', 'expense'] and txn_data['party_type'] == 'vendor':
        tds_rules = await get_tax_rules(db, company_id, 'tds')
        for rule in tds_rules:
            # Apply rule conditions
            if TaxCalculator.evaluate_rule(rule['condition_json'], txn_data):
                section = rule['action_json'].get('section')
                rate = TaxCalculator.get_tds_rate(section, txn_data['subtotal'], '2024-25')
                if rate > 0:
                    tds_amount = txn_data['subtotal'] * rate / 100
                    taxes['tds'].append({
                        'section': section,
                        'rate': rate,
                        'amount': tds_amount,
                        'period': TaxCalculator.get_quarter(txn_data['txn_date'])
                    })

    # TCS Calculation for receipts
    if txn_data['txn_type'] in ['receipt', 'sales_invoice'] and txn_data['party_type'] == 'customer':
        tcs_rules = await get_tax_rules(db, company_id, 'tcs')
        for rule in tcs_rules:
            if TaxCalculator.evaluate_rule(rule['condition_json'], txn_data):
                section = rule['action_json'].get('section')
                rate = TaxCalculator.get_tcs_rate(section, txn_data['subtotal'])
                if rate > 0:
                    tcs_amount = txn_data['subtotal'] * rate / 100
                    taxes['tcs'].append({
                        'section': section,
                        'rate': rate,
                        'amount': tcs_amount,
                        'period': TaxCalculator.get_quarter(txn_data['txn_date'])
                    })

    return taxes

# API Endpoints

# Tax Configuration APIs
@app.post('/compliance/tax-rates')
async def create_tax_rate(
    config: TaxRateConfig,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Create or update tax rate configuration"""
    query = text("""
        INSERT INTO tax_rates (company_id, tax_type, section_code, hsn_sac_code, rate, effective_from, effective_to)
        VALUES (:company_id, :tax_type, :section_code, :hsn_sac_code, :rate, :effective_from, :effective_to)
        ON CONFLICT (company_id, tax_type, section_code, hsn_sac_code, effective_from)
        DO UPDATE SET rate = EXCLUDED.rate, effective_to = EXCLUDED.effective_to, updated_at = now()
        RETURNING tax_rate_id
    """)

    result = await db.execute(query, {
        'company_id': current_context.company_id,
        'tax_type': config.tax_type,
        'section_code': config.section_code,
        'hsn_sac_code': config.hsn_sac_code,
        'rate': config.rate,
        'effective_from': config.effective_from,
        'effective_to': config.effective_to
    })

    tax_rate_id = result.scalar()
    await db.commit()

    return {'tax_rate_id': tax_rate_id, 'message': 'Tax rate configured successfully'}

@app.post('/compliance/tax-rules')
async def create_tax_rule(
    config: TaxRuleConfig,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Create tax rule"""
    query = text("""
        INSERT INTO tax_rules (company_id, rule_name, tax_type, condition_json, action_json, priority)
        VALUES (:company_id, :rule_name, :tax_type, :condition_json, :action_json, :priority)
        RETURNING tax_rule_id
    """)

    result = await db.execute(query, {
        'company_id': current_context.company_id,
        'rule_name': config.rule_name,
        'tax_type': config.tax_type,
        'condition_json': json.dumps(config.condition_json),
        'action_json': json.dumps(config.action_json),
        'priority': config.priority
    })

    tax_rule_id = result.scalar()
    await db.commit()

    return {'tax_rule_id': tax_rule_id, 'message': 'Tax rule created successfully'}

# GST APIs
@app.post('/compliance/gst/calculate/{transaction_id}')
async def calculate_gst_for_transaction(
    transaction_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Calculate and store GST liability for a transaction"""
    taxes = await calculate_transaction_taxes(db, current_context.company_id, transaction_id)

    if not taxes['gst']:
        return {'message': 'No GST applicable for this transaction'}

    inserted_liabilities = []
    for gst_item in taxes['gst']:
        # Get transaction details for GSTIN
        txn_query = text("""
            SELECT p.gstin as party_gstin, c.gstin as company_gstin
            FROM transactions t
            JOIN parties p ON t.party_id = p.party_id
            JOIN companies c ON t.company_id = c.company_id
            WHERE t.transaction_id = :transaction_id
        """)

        txn_result = await db.execute(txn_query, {'transaction_id': transaction_id})
        gstin_row = txn_result.mappings().first()
        if not gstin_row:
            raise HTTPException(status_code=404, detail='Transaction details not found')
        gstin_data = dict(gstin_row)

        gstin = gstin_data['party_gstin'] if gst_item['is_input'] else gstin_data['company_gstin']

        if not TaxCalculator.validate_gstin(gstin):
            raise HTTPException(status_code=400, detail=f'Invalid GSTIN: {gstin}')

        liability_query = text("""
            INSERT INTO gst_liability (company_id, transaction_id, gstin, component, taxable_amount, rate, amount, period, is_input)
            VALUES (:company_id, :transaction_id, :gstin, :component, :taxable_amount, :rate, :amount, :period, :is_input)
            ON CONFLICT (company_id, transaction_id, component)
            DO UPDATE SET taxable_amount = EXCLUDED.taxable_amount, rate = EXCLUDED.rate, amount = EXCLUDED.amount
            RETURNING gst_liability_id
        """)

        result = await db.execute(liability_query, {
            'company_id': current_context.company_id,
            'transaction_id': transaction_id,
            'gstin': gstin,
            'component': gst_item['component'],
            'taxable_amount': gst_item['taxable_amount'],
            'rate': gst_item['rate'],
            'amount': gst_item['amount'],
            'period': gst_item['period'],
            'is_input': gst_item['is_input']
        })

        liability_id = result.scalar()
        inserted_liabilities.append(liability_id)

    await db.commit()
    return {'liabilities_created': len(inserted_liabilities), 'liability_ids': inserted_liabilities}

@app.post('/compliance/gst/returns')
async def create_gst_return(
    request: GSTReturnRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Generate GST return for given period"""
    # Calculate due date based on return type
    year, month = map(int, request.period.split('-'))
    if request.return_type == 'GSTR1':
        due_date = date(year, month + 1, 11)  # 11th of next month
    elif request.return_type == 'GSTR3B':
        due_date = date(year, month + 1, 20)  # 20th of next month
    else:
        due_date = date(year, month + 1, 31)  # 31st of next month

    # Aggregate GST data for the period
    summary_query = text("""
        SELECT
            SUM(CASE WHEN is_input THEN 0 ELSE taxable_amount END) as output_taxable,
            SUM(CASE WHEN is_input THEN 0 ELSE amount END) as output_tax,
            SUM(CASE WHEN is_input THEN taxable_amount ELSE 0 END) as input_taxable,
            SUM(CASE WHEN is_input THEN amount ELSE 0 END) as input_tax
        FROM gst_liability
        WHERE company_id = :company_id AND period = :period
    """)

    summary_result = await db.execute(summary_query, {
        'company_id': current_context.company_id,
        'period': request.period
    })

    summary_row = summary_result.mappings().first()
    summary = dict(summary_row) if summary_row else {}

    # Create return record
    return_query = text("""
        INSERT INTO gst_returns (company_id, return_type, period, due_date, total_taxable_value, total_tax_amount, created_by, updated_by)
        VALUES (:company_id, :return_type, :period, :due_date, :total_taxable, :total_tax, :user_id, :user_id)
        RETURNING gst_return_id
    """)

    result = await db.execute(return_query, {
        'company_id': current_context.company_id,
        'return_type': request.return_type,
        'period': request.period,
        'due_date': due_date,
        'total_taxable': (summary.get('output_taxable') if isinstance(summary, dict) else None) or 0,
        'total_tax': (summary.get('output_tax') if isinstance(summary, dict) else None) or 0,
        'user_id': current_context.user_id
    })

    return_id = result.scalar()
    if return_id is None:
        raise HTTPException(status_code=500, detail='Failed to create GST return')
    await db.commit()

    return GSTReturnResponse(
        gst_return_id=return_id,
        return_type=request.return_type,
        period=request.period,
        status='generated',
        total_taxable_value=(summary.get('output_taxable') if isinstance(summary, dict) else None) or 0,
        total_tax_amount=(summary.get('output_tax') if isinstance(summary, dict) else None) or 0,
        filing_date=None,
        due_date=due_date
    )

@app.get('/compliance/gst/returns')
async def list_gst_returns(
    period: Optional[str] = None,
    return_type: Optional[str] = None,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """List GST returns"""
    query = """
        SELECT gst_return_id, return_type, period, status, total_taxable_value, total_tax_amount, filing_date, due_date
        FROM gst_returns
        WHERE company_id = :company_id
    """
    params: Dict[str, Any] = {'company_id': str(current_context.company_id)}

    if period:
        query += " AND period = :period"
        params['period'] = period

    if return_type:
        query += " AND return_type = :return_type"
        params['return_type'] = return_type

    query += " ORDER BY period DESC, return_type"

    result = await db.execute(text(query), params)
    returns = [GSTReturnResponse(**dict(row)) for row in result.mappings()]

    return {'returns': returns}

# TDS APIs
@app.post('/compliance/tds/calculate/{transaction_id}')
async def calculate_tds_for_transaction(
    transaction_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Calculate and store TDS deduction for a transaction"""
    taxes = await calculate_transaction_taxes(db, current_context.company_id, transaction_id)

    if not taxes['tds']:
        return {'message': 'No TDS applicable for this transaction'}

    # Get transaction and party details
    txn_query = text("""
        SELECT t.subtotal, p.party_name, p.gstin
        FROM transactions t
        JOIN parties p ON t.party_id = p.party_id
        WHERE t.transaction_id = :transaction_id
    """)

    txn_result = await db.execute(txn_query, {'transaction_id': transaction_id})
    txn_data_row = txn_result.mappings().first()
    if not txn_data_row:
        raise HTTPException(status_code=404, detail='Transaction details not found')
    txn_data = dict(txn_data_row)

    inserted_deductions = []
    for tds_item in taxes['tds']:
        deduction_query = text("""
            INSERT INTO tds_deductions (
                company_id, transaction_id, section, deductee_name, deductee_pan, deductee_gstin,
                payment_amount, tds_rate, tds_amount, total_tax, period, created_at
            )
            VALUES (
                :company_id, :transaction_id, :section, :deductee_name, :deductee_pan, :deductee_gstin,
                :payment_amount, :tds_rate, :tds_amount, :total_tax, :period, now()
            )
            RETURNING tds_deduction_id
        """)

        # Extract PAN from GSTIN if available
        pan = txn_data['gstin'][2:12] if txn_data['gstin'] else None

        result = await db.execute(deduction_query, {
            'company_id': current_context.company_id,
            'transaction_id': transaction_id,
            'section': tds_item['section'],
            'deductee_name': txn_data['party_name'],
            'deductee_pan': pan,
            'deductee_gstin': txn_data['gstin'],
            'payment_amount': txn_data['subtotal'],
            'tds_rate': tds_item['rate'],
            'tds_amount': tds_item['amount'],
            'total_tax': tds_item['amount'],  # Simplified, add surcharge/cess later
            'period': tds_item['period']
        })

        deduction_id = result.scalar()
        inserted_deductions.append(deduction_id)

    await db.commit()
    return {'deductions_created': len(inserted_deductions), 'deduction_ids': inserted_deductions}

@app.post('/compliance/tds/returns')
async def create_tds_return(
    request: TDSReturnRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Generate TDS return for given period"""
    # Calculate due date (31st July for Q4, 31st Oct for Q1, 31st Jan for Q2, 31st May for Q3)
    year, quarter = request.period.split('-Q')
    year = int(year)
    quarter = int(quarter)

    due_dates = {
        1: date(year, 10, 31),  # Q1 - Oct 31
        2: date(year + 1, 1, 31),  # Q2 - Jan 31 next year
        3: date(year + 1, 5, 31),  # Q3 - May 31 next year
        4: date(year + 1, 7, 31),  # Q4 - Jul 31 next year
    }
    due_date = due_dates[quarter]

    # Aggregate TDS data for the period
    summary_query = text("""
        SELECT SUM(tds_amount) as total_deductions, SUM(total_tax) as total_deposits
        FROM tds_deductions
        WHERE company_id = :company_id AND period = :period
    """)

    summary_result = await db.execute(summary_query, {
        'company_id': current_context.company_id,
        'period': request.period
    })

    summary_row = summary_result.mappings().first()
    summary = dict(summary_row) if summary_row else {}

    # Create return record
    return_query = text("""
        INSERT INTO tds_returns (company_id, form_no, period, due_date, total_deductions, total_deposits, created_by, updated_by)
        VALUES (:company_id, :form_no, :period, :due_date, :total_deductions, :total_deposits, :user_id, :user_id)
        RETURNING tds_return_id
    """)

    result = await db.execute(return_query, {
        'company_id': current_context.company_id,
        'form_no': request.form_no,
        'period': request.period,
        'due_date': due_date,
        'total_deductions': (summary.get('total_deductions') if isinstance(summary, dict) else None) or 0,
        'total_deposits': (summary.get('total_deposits') if isinstance(summary, dict) else None) or 0,
        'user_id': current_context.user_id
    })

    return_id = result.scalar()
    await db.commit()

    return {
        'tds_return_id': return_id,
        'form_no': request.form_no,
        'period': request.period,
        'status': 'generated',
        'total_deductions': (summary.get('total_deductions') if isinstance(summary, dict) else None) or 0,
        'due_date': due_date
    }

# TCS APIs
@app.post('/compliance/tcs/calculate/{transaction_id}')
async def calculate_tcs_for_transaction(
    transaction_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Calculate and store TCS collection for a transaction"""
    taxes = await calculate_transaction_taxes(db, current_context.company_id, transaction_id)

    if not taxes['tcs']:
        return {'message': 'No TCS applicable for this transaction'}

    # Get transaction and party details
    txn_query = text("""
        SELECT t.subtotal, p.party_name, p.gstin
        FROM transactions t
        JOIN parties p ON t.party_id = p.party_id
        WHERE t.transaction_id = :transaction_id
    """)

    txn_result = await db.execute(txn_query, {'transaction_id': transaction_id})
    txn_data_row = txn_result.mappings().first()
    if not txn_data_row:
        raise HTTPException(status_code=404, detail='Transaction details not found')
    txn_data = dict(txn_data_row)

    inserted_collections = []
    for tcs_item in taxes['tcs']:
        collection_query = text("""
            INSERT INTO tcs_collections (
                company_id, transaction_id, section, collectee_name, collectee_pan, collectee_gstin,
                receipt_amount, tcs_rate, tcs_amount, total_tax, period, created_at
            )
            VALUES (
                :company_id, :transaction_id, :section, :collectee_name, :collectee_pan, :collectee_gstin,
                :receipt_amount, :tcs_rate, :tcs_amount, :total_tax, :period, now()
            )
            RETURNING tcs_collection_id
        """)

        # Extract PAN from GSTIN if available
        pan = txn_data['gstin'][2:12] if txn_data['gstin'] else None

        result = await db.execute(collection_query, {
            'company_id': current_context.company_id,
            'transaction_id': transaction_id,
            'section': tcs_item['section'],
            'collectee_name': txn_data['party_name'],
            'collectee_pan': pan,
            'collectee_gstin': txn_data['gstin'],
            'receipt_amount': txn_data['subtotal'],
            'tcs_rate': tcs_item['rate'],
            'tcs_amount': tcs_item['amount'],
            'total_tax': tcs_item['amount'],  # Simplified
            'period': tcs_item['period']
        })

        collection_id = result.scalar()
        inserted_collections.append(collection_id)

    await db.commit()
    return {'collections_created': len(inserted_collections), 'collection_ids': inserted_collections}

# Advance Tax APIs
@app.post('/compliance/advance-tax')
async def create_advance_tax_liability(
    assessment_year: str = Query(..., regex=r'^\d{4}-\d{2}$'),
    estimated_income: float = Query(..., gt=0),
    quarter: str = Query(..., regex=r'^Q[1-4]$'),
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Create advance tax liability"""
    tax_calc = TaxCalculator.calculate_advance_tax(estimated_income, assessment_year)

    # Calculate due date based on quarter
    year = int(assessment_year.split('-')[0])
    quarter_num = int(quarter[1])

    due_dates = {
        1: date(year, 7, 31),    # Q1 - Jul 31
        2: date(year, 10, 31),   # Q2 - Oct 31
        3: date(year, 1, 31),    # Q3 - Jan 31 next year
        4: date(year, 3, 31),    # Q4 - Mar 31 next year
    }
    due_date = due_dates[quarter_num]
    if quarter_num <= 2:
        due_date = due_date.replace(year=year)
    else:
        due_date = due_date.replace(year=year + 1)

    liability_query = text("""
        INSERT INTO advance_tax_liability (
            company_id, assessment_year, quarter, estimated_income, tax_rate,
            advance_tax_due, surcharge, cess, total_tax, due_date
        )
        VALUES (
            :company_id, :assessment_year, :quarter, :estimated_income, :tax_rate,
            :advance_tax_due, :surcharge, :cess, :total_tax, :due_date
        )
        ON CONFLICT (company_id, assessment_year, quarter)
        DO UPDATE SET
            estimated_income = EXCLUDED.estimated_income,
            tax_rate = EXCLUDED.tax_rate,
            advance_tax_due = EXCLUDED.advance_tax_due,
            surcharge = EXCLUDED.surcharge,
            cess = EXCLUDED.cess,
            total_tax = EXCLUDED.total_tax,
            updated_at = now()
        RETURNING advance_tax_id
    """)

    result = await db.execute(liability_query, {
        'company_id': current_context.company_id,
        'assessment_year': assessment_year,
        'quarter': quarter,
        'estimated_income': estimated_income,
        'tax_rate': tax_calc['tax_rate'],
        'advance_tax_due': tax_calc['tax_amount'],
        'surcharge': tax_calc['surcharge'],
        'cess': tax_calc['cess'],
        'total_tax': tax_calc['total_tax'],
        'due_date': due_date
    })

    tax_id = result.scalar()
    await db.commit()

    return {
        'advance_tax_id': tax_id,
        'assessment_year': assessment_year,
        'quarter': quarter,
        'total_tax': tax_calc['total_tax'],
        'due_date': due_date
    }

@app.get('/compliance/advance-tax')
async def get_advance_tax_liabilities(
    assessment_year: Optional[str] = None,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Get advance tax liabilities"""
    query = """
        SELECT advance_tax_id, assessment_year, quarter, estimated_income, advance_tax_due,
               total_tax, due_date, paid_amount, balance, status
        FROM advance_tax_liability
        WHERE company_id = :company_id
    """
    params: Dict[str, Any] = {'company_id': str(current_context.company_id)}

    if assessment_year:
        query += " AND assessment_year = :assessment_year"
        params['assessment_year'] = assessment_year

    query += " ORDER BY assessment_year DESC, quarter"

    result = await db.execute(text(query), params)
    liabilities = [AdvanceTaxLiability(**dict(row)) for row in result.mappings()]

    return {'liabilities': liabilities}

# Report APIs
@app.post('/compliance/reports')
async def generate_compliance_report(
    request: ComplianceReportRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Generate compliance reports"""
    filters = request.filters or {}
    if request.report_type == 'gst_liability':
        return await generate_gst_liability_report(db, current_context.company_id, request.period, filters)
    elif request.report_type == 'tds_summary':
        return await generate_tds_summary_report(db, current_context.company_id, request.period, filters)
    elif request.report_type == 'tcs_summary':
        return await generate_tcs_summary_report(db, current_context.company_id, request.period, filters)
    elif request.report_type == 'advance_tax':
        return await generate_advance_tax_report(db, current_context.company_id, request.period, filters)
    elif request.report_type == 'reconciliation':
        return await generate_reconciliation_report(db, current_context.company_id, request.period, filters)
    else:
        raise HTTPException(status_code=400, detail='Invalid report type')

async def generate_gst_liability_report(db: AsyncSession, company_id: UUID, period: str, filters: Optional[Dict[str, Any]]) -> Dict:
    """Generate GST liability report"""
    query = """
        SELECT component, SUM(taxable_amount) as total_taxable, SUM(amount) as total_tax,
               COUNT(*) as transaction_count
        FROM gst_liability
        WHERE company_id = :company_id AND period = :period
        GROUP BY component
        ORDER BY component
    """

    result = await db.execute(text(query), {'company_id': company_id, 'period': period})
    data = [dict(row) for row in result.mappings()]

    return {
        'report_type': 'gst_liability',
        'period': period,
        'company_id': company_id,
        'data': data,
        'generated_at': datetime.utcnow()
    }

async def generate_tds_summary_report(db: AsyncSession, company_id: UUID, period: str, filters: Optional[Dict[str, Any]]) -> Dict:
    """Generate TDS summary report"""
    query = """
        SELECT section, SUM(tds_amount) as total_tds, SUM(total_tax) as total_tax_deposited,
               COUNT(*) as deduction_count
        FROM tds_deductions
        WHERE company_id = :company_id AND period = :period
        GROUP BY section
        ORDER BY section
    """

    result = await db.execute(text(query), {'company_id': company_id, 'period': period})
    data = [dict(row) for row in result.mappings()]

    return {
        'report_type': 'tds_summary',
        'period': period,
        'company_id': company_id,
        'data': data,
        'generated_at': datetime.utcnow()
    }

async def generate_tcs_summary_report(db: AsyncSession, company_id: UUID, period: str, filters: Optional[Dict[str, Any]]) -> Dict:
    """Generate TCS summary report"""
    query = """
        SELECT section, SUM(tcs_amount) as total_tcs, SUM(total_tax) as total_tax_collected,
               COUNT(*) as collection_count
        FROM tcs_collections
        WHERE company_id = :company_id AND period = :period
        GROUP BY section
        ORDER BY section
    """

    result = await db.execute(text(query), {'company_id': company_id, 'period': period})
    data = [dict(row) for row in result.mappings()]

    return {
        'report_type': 'tcs_summary',
        'period': period,
        'company_id': company_id,
        'data': data,
        'generated_at': datetime.utcnow()
    }

async def generate_advance_tax_report(db: AsyncSession, company_id: UUID, period: str, filters: Optional[Dict[str, Any]]) -> Dict:
    """Generate advance tax report"""
    query = """
        SELECT assessment_year, quarter, estimated_income, total_tax, paid_amount, balance, status, due_date
        FROM advance_tax_liability
        WHERE company_id = :company_id
        ORDER BY assessment_year DESC, quarter
    """

    result = await db.execute(text(query), {'company_id': company_id})
    data = [dict(row) for row in result.mappings()]

    return {
        'report_type': 'advance_tax',
        'company_id': company_id,
        'data': data,
        'generated_at': datetime.utcnow()
    }

async def generate_reconciliation_report(db: AsyncSession, company_id: UUID, period: str, filters: Optional[Dict[str, Any]]) -> Dict:
    """Generate tax reconciliation report"""
    # Compare book vs actual tax payments
    reconciliation_data = {
        'gst_reconciliation': await reconcile_gst(db, company_id, period),
        'tds_reconciliation': await reconcile_tds(db, company_id, period),
        'tcs_reconciliation': await reconcile_tcs(db, company_id, period)
    }

    return {
        'report_type': 'reconciliation',
        'period': period,
        'company_id': company_id,
        'data': reconciliation_data,
        'generated_at': datetime.utcnow()
    }

async def reconcile_gst(db: AsyncSession, company_id: UUID, period: str) -> Dict:
    """Reconcile GST - book vs paid"""
    book_query = text("""
        SELECT SUM(amount) as book_tax
        FROM gst_liability
        WHERE company_id = :company_id AND period = :period AND NOT is_input
    """)

    # In production, you'd have a payments table to track actual GST payments
    # For now, return book tax only
    result = await db.execute(book_query, {'company_id': company_id, 'period': period})
    book_tax = result.scalar() or 0

    return {
        'book_tax': book_tax,
        'paid_tax': 0,  # Would come from payment records
        'difference': -book_tax
    }

async def reconcile_tds(db: AsyncSession, company_id: UUID, period: str) -> Dict:
    """Reconcile TDS - deducted vs deposited"""
    deducted_query = text("""
        SELECT SUM(tds_amount) as deducted
        FROM tds_deductions
        WHERE company_id = :company_id AND period = :period
    """)

    deposited_query = text("""
        SELECT SUM(total_tax) as deposited
        FROM tds_deductions
        WHERE company_id = :company_id AND period = :period AND deposited = TRUE
    """)

    deducted_result = await db.execute(deducted_query, {'company_id': company_id, 'period': period})
    deposited_result = await db.execute(deposited_query, {'company_id': company_id, 'period': period})

    deducted = deducted_result.scalar() or 0
    deposited = deposited_result.scalar() or 0

    return {
        'deducted': deducted,
        'deposited': deposited,
        'difference': deducted - deposited
    }

async def reconcile_tcs(db: AsyncSession, company_id: UUID, period: str) -> Dict:
    """Reconcile TCS - collected vs deposited"""
    collected_query = text("""
        SELECT SUM(tcs_amount) as collected
        FROM tcs_collections
        WHERE company_id = :company_id AND period = :period
    """)

    deposited_query = text("""
        SELECT SUM(total_tax) as deposited
        FROM tcs_collections
        WHERE company_id = :company_id AND period = :period AND deposited = TRUE
    """)

    collected_result = await db.execute(collected_query, {'company_id': company_id, 'period': period})
    deposited_result = await db.execute(deposited_query, {'company_id': company_id, 'period': period})

    collected = collected_result.scalar() or 0
    deposited = deposited_result.scalar() or 0

    return {
        'collected': collected,
        'deposited': deposited,
        'difference': collected - deposited
    }

# Threshold monitoring
@app.get('/compliance/thresholds/check')
async def check_compliance_thresholds(
    current_context: TenantContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    """Check if company has breached any compliance thresholds"""
    alerts = []

    # GST threshold check
    gst_query = text("""
        SELECT SUM(CASE WHEN is_input THEN 0 ELSE taxable_amount END) as turnover
        FROM gst_liability
        WHERE company_id = :company_id AND period >= :start_period
    """)

    current_period = date.today().replace(day=1)
    start_period = (current_period - timedelta(days=365)).strftime('%Y-%m')

    gst_result = await db.execute(gst_query, {
        'company_id': current_context.company_id,
        'start_period': start_period
    })

    turnover = gst_result.scalar() or 0

    # Check against GST threshold (₹40 lakhs for services, ₹20 lakhs for goods)
    gst_threshold = 4000000  # ₹40 lakhs
    if turnover > gst_threshold:
        alerts.append({
            'type': 'gst_threshold_breach',
            'message': f'GST turnover threshold breached: ₹{turnover:,.0f} > ₹{gst_threshold:,.0f}',
            'severity': 'high'
        })

    # TDS threshold checks would go here
    # Advance tax due date checks would go here

    return {'alerts': alerts, 'checked_at': datetime.utcnow()}

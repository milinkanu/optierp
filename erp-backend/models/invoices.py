from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceItemCreate(BaseModel):
    description: str
    hsn_sac: Optional[str] = None
    account_id: Optional[UUID] = None
    quantity: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]
    unit_price: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]
    discount_amount: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] = Decimal("0")
    gst_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]
    tds_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")
    tcs_rate: Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)] = Decimal("0")


class InvoiceCreateRequest(BaseModel):
    invoice_type: str
    invoice_date: date
    due_date: Optional[date] = None
    billing_party_id: Optional[UUID] = None
    shipping_party_id: Optional[UUID] = None
    currency: str = "INR"
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] = Decimal("1")
    items: List[InvoiceItemCreate]
    meta: Optional[dict] = None


class InvoiceResponse(BaseModel):
    invoice_id: UUID
    invoice_number: str
    invoice_type: str
    status: str
    invoice_grand_total: float
    paid_amount: float
    balance_due: float
    created_at: datetime


class PaymentAllocationRequest(BaseModel):
    payment_transaction_id: UUID
    allocated_amount: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
    currency: str = "INR"
    exchange_rate: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=8)] = Decimal("1")


from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import DocumentStatus, PaymentMethod, TransitionAction
from app.schemas.common import ORMBase


class InvoiceLineInput(BaseModel):
    product_id: UUID | None = None
    description: str | None = None
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal | None = None
    tax_rate: Decimal | None = None


class InvoiceCreate(BaseModel):
    customer_id: UUID
    issue_date: date
    due_date: date | None = None
    payment_method: PaymentMethod = PaymentMethod.CASH
    currency: str = Field(default="COP", max_length=3)
    lines: List[InvoiceLineInput] = Field(min_length=1)
    notes: str | None = None


class InvoiceUpdate(BaseModel):
    customer_id: UUID | None = None
    issue_date: date | None = None
    due_date: date | None = None
    payment_method: PaymentMethod | None = None
    currency: str | None = None
    lines: List[InvoiceLineInput] | None = None
    notes: str | None = None


class InvoiceLineResponse(ORMBase):
    id: UUID
    product_id: UUID | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class InvoiceResponse(ORMBase):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    number: str
    prefix: str
    status: DocumentStatus
    issue_date: date
    due_date: date | None
    payment_method: PaymentMethod
    currency: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    notes: str | None
    cufe: str | None
    signed_at: datetime | None
    submitted_at: datetime | None
    dian_response: dict[str, Any] | None
    lines: List[InvoiceLineResponse] = []


class TransitionRequest(BaseModel):
    action: TransitionAction


class DocumentEventResponse(ORMBase):
    id: UUID
    document_type: str
    document_id: UUID
    event_type: str
    from_status: str | None
    to_status: str | None
    user_id: UUID | None
    event_metadata: dict[str, Any] | None = None
    created_at: datetime

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import DocumentStatus
from app.schemas.common import ORMBase
from app.schemas.invoice import InvoiceLineInput, TransitionRequest

__all__ = ["DebitNoteCreate", "DebitNoteResponse", "TransitionRequest"]


class DebitNoteCreate(BaseModel):
    invoice_id: UUID
    customer_id: UUID | None = None
    issue_date: date
    reason_code: str = Field(max_length=10)
    reason_text: str | None = None
    lines: List[InvoiceLineInput] = Field(min_length=1)


class DebitNoteLineResponse(ORMBase):
    id: UUID
    product_id: UUID | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class DebitNoteResponse(ORMBase):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    invoice_id: UUID
    number: str
    prefix: str
    status: DocumentStatus
    issue_date: date
    reason_code: str
    reason_text: str | None
    currency: str
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    cude: str | None
    signed_at: datetime | None
    submitted_at: datetime | None
    dian_response: dict[str, Any] | None
    lines: List[DebitNoteLineResponse] = []

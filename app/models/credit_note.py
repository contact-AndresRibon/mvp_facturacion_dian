import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import JSON, Column, Numeric, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.domain.enums import DocumentStatus


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CreditNote(SQLModel, table=True):
    __tablename__ = "credit_notes"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_credit_note_tenant_number"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    invoice_id: uuid.UUID = Field(foreign_key="invoices.id", index=True)
    number: str = Field(max_length=50, index=True)
    prefix: str = Field(max_length=20)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, index=True)
    issue_date: date
    reason_code: str = Field(max_length=10)  # TODO-DIAN: catalog
    reason_text: Optional[str] = Field(default=None, max_length=500)
    currency: str = Field(default="COP", max_length=3)
    subtotal: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    tax_total: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    total: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    cude: Optional[str] = Field(default=None, max_length=255)  # TODO-DIAN: official formula
    signed_at: Optional[datetime] = Field(default=None)
    submitted_at: Optional[datetime] = Field(default=None)
    dian_response: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    xml_path: Optional[str] = Field(default=None, max_length=500)
    pdf_path: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    lines: list["CreditNoteLine"] = Relationship(back_populates="credit_note")


class CreditNoteLine(SQLModel, table=True):
    __tablename__ = "credit_note_lines"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    credit_note_id: uuid.UUID = Field(foreign_key="credit_notes.id", index=True)
    product_id: Optional[uuid.UUID] = Field(default=None, foreign_key="products.id")
    description: str = Field(max_length=500)
    quantity: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    unit_price: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    tax_rate: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    line_subtotal: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    line_tax: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    line_total: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))

    credit_note: Optional[CreditNote] = Relationship(back_populates="lines")

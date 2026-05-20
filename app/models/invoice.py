import uuid
import sqlalchemy as sa
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import JSON, Column, Numeric, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.domain.enums import DocumentStatus, PaymentMethod



def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("tenant_id", "number", name="uq_invoice_tenant_number"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    number: str = Field(max_length=50, index=True)
    prefix: str = Field(max_length=20)
    status: DocumentStatus = Field(default=DocumentStatus.DRAFT, index=True)
    issue_date: date
    due_date: Optional[date] = Field(default=None)

    payment_method: PaymentMethod = Field(
    default=PaymentMethod.CASH,
    sa_column=Column(sa.String(20), nullable=False, server_default="cash")
    )

    currency: str = Field(default="COP", max_length=3)
    subtotal: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    tax_total: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    total: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    notes: Optional[str] = Field(default=None, max_length=2000)
    cufe: Optional[str] = Field(default=None, max_length=255)  # TODO-DIAN: official formula
    signed_at: Optional[datetime] = Field(default=None)
    submitted_at: Optional[datetime] = Field(default=None)
    dian_response: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    xml_path: Optional[str] = Field(default=None, max_length=500)
    pdf_path: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    lines: list["InvoiceLine"] = Relationship(back_populates="invoice")


class InvoiceLine(SQLModel, table=True):
    __tablename__ = "invoice_lines"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    invoice_id: uuid.UUID = Field(foreign_key="invoices.id", index=True)
    product_id: Optional[uuid.UUID] = Field(default=None, foreign_key="products.id")
    description: str = Field(max_length=500)
    quantity: Decimal = Field(sa_column=Column(Numeric(18, 4), nullable=False))
    unit_price: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    tax_rate: Decimal = Field(sa_column=Column(Numeric(5, 2), nullable=False))
    line_subtotal: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    line_tax: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    line_total: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))

    invoice: Optional[Invoice] = Relationship(back_populates="lines")

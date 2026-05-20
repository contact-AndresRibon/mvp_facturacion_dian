import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Numeric


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    code: str = Field(max_length=50, index=True)
    name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    unit_price: Decimal = Field(sa_column=Column(Numeric(18, 2), nullable=False))
    tax_rate: Decimal = Field(default=Decimal("19.00"), sa_column=Column(Numeric(5, 2)))
    unit_code: str = Field(default="EA", max_length=10)  # TODO-DIAN: UNSPSC/unit catalog
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class ProductCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    unit_price: Decimal = Field(gt=0)
    tax_rate: Decimal = Field(default=Decimal("19.00"), ge=0, le=100)
    unit_code: str = Field(default="EA", max_length=10)


class ProductUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None
    unit_price: Decimal | None = Field(default=None, gt=0)
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100)
    unit_code: str | None = None
    is_active: bool | None = None


class ProductResponse(ORMBase):
    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None
    unit_price: Decimal
    tax_rate: Decimal
    unit_code: str
    is_active: bool

from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBase


class TenantUpdate(BaseModel):
    legal_name: str | None = Field(default=None, min_length=2, max_length=255)
    trade_name: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    city_code: str | None = None
    regime_code: str | None = None
    invoice_prefix: str | None = Field(default=None, max_length=20)
    credit_note_prefix: str | None = Field(default=None, max_length=20)
    debit_note_prefix: str | None = Field(default=None, max_length=20)
    resolution_number: str | None = Field(default=None, max_length=50)
    resolution_valid_from: date | None = None
    resolution_valid_to: date | None = None


class TenantResponse(ORMBase):
    id: UUID
    legal_name: str
    trade_name: str | None
    nit: str
    dv: str | None
    email: str
    address: str | None
    city_code: str | None
    regime_code: str | None
    invoice_prefix: str | None
    credit_note_prefix: str | None
    debit_note_prefix: str | None
    resolution_number: str | None
    resolution_valid_from: date | None
    resolution_valid_to: date | None
    is_active: bool
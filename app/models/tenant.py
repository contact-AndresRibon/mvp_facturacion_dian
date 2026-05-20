import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    legal_name: str = Field(max_length=255)
    trade_name: Optional[str] = Field(default=None, max_length=255)
    nit: str = Field(max_length=20, index=True)
    dv: Optional[str] = Field(default=None, max_length=1)
    email: str = Field(max_length=255)
    address: Optional[str] = Field(default=None, max_length=500)
    city_code: Optional[str] = Field(default=None, max_length=10)  # TODO-DIAN: catalog
    regime_code: Optional[str] = Field(default=None, max_length=10)  # TODO-DIAN: catalog
    invoice_prefix: Optional[str] = Field(default=None, max_length=20)
    credit_note_prefix: Optional[str] = Field(default=None, max_length=20)
    debit_note_prefix: Optional[str] = Field(default=None, max_length=20)
    resolution_number: Optional[str] = Field(default=None, max_length=50)  # TODO-DIAN
    resolution_valid_from: Optional[date] = Field(default=None)
    resolution_valid_to: Optional[date] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

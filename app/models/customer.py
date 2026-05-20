import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(SQLModel, table=True):
    __tablename__ = "customers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    document_type: str = Field(max_length=10)  # TODO-DIAN: catalog (CC, NIT, etc.)
    document_number: str = Field(max_length=50, index=True)
    name: str = Field(max_length=255)
    email: Optional[str] = Field(default=None, max_length=255)
    address: Optional[str] = Field(default=None, max_length=500)
    phone: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

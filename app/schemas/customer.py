from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMBase


class CustomerCreate(BaseModel):
    document_type: str = Field(max_length=10)
    document_number: str = Field(min_length=3, max_length=50)
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    address: str | None = None
    phone: str | None = None


class CustomerUpdate(BaseModel):
    document_type: str | None = None
    document_number: str | None = None
    name: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class CustomerResponse(ORMBase):
    id: UUID
    tenant_id: UUID
    document_type: str
    document_number: str
    name: str
    email: str | None
    address: str | None
    phone: str | None
    is_active: bool

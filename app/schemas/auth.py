from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.domain.enums import UserRole
from app.schemas.common import ORMBase


class RegisterRequest(BaseModel):
    legal_name: str = Field(min_length=2, max_length=255)
    trade_name: str | None = None
    nit: str = Field(min_length=5, max_length=20)
    dv: str | None = Field(default=None, max_length=1)
    email: EmailStr
    address: str | None = None
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)
    admin_full_name: str = Field(min_length=2, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(ORMBase):
    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool

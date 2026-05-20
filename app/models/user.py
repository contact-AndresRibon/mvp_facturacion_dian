import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel

from app.domain.enums import UserRole


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    email: str = Field(max_length=255, index=True)
    hashed_password: str = Field(max_length=255)
    full_name: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.ADMIN)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

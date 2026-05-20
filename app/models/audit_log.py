import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    action: str = Field(max_length=100, index=True)
    resource_type: str = Field(max_length=50, index=True)
    resource_id: Optional[str] = Field(default=None, max_length=50)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    request_id: Optional[str] = Field(default=None, max_length=50, index=True)
    details: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now, index=True)

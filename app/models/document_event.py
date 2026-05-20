import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.domain.enums import DocumentEventType, DocumentType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentEvent(SQLModel, table=True):
    __tablename__ = "document_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    document_type: DocumentType = Field(index=True)
    document_id: uuid.UUID = Field(index=True)
    event_type: DocumentEventType = Field(index=True)
    from_status: Optional[str] = Field(default=None, max_length=20)
    to_status: Optional[str] = Field(default=None, max_length=20)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    event_metadata: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)

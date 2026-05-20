import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.domain.enums import SequenceDocType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentSequence(SQLModel, table=True):
    __tablename__ = "document_sequences"
    __table_args__ = (
        UniqueConstraint("tenant_id", "doc_type", "prefix", name="uq_sequence_tenant_type_prefix"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    doc_type: SequenceDocType = Field(index=True)
    prefix: str = Field(max_length=20)
    last_number: int = Field(default=0)
    updated_at: datetime = Field(default_factory=utc_now)

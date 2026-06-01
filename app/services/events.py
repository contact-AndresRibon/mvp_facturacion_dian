import uuid
from typing import Any, Optional

from sqlmodel import Session

from app.domain.enums import DocumentEventType, DocumentType
from app.models.document_event import DocumentEvent


def record_event(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    document_type: DocumentType,
    document_id: uuid.UUID,
    event_type: DocumentEventType,
    from_status: Optional[str],
    to_status: Optional[str],
    event_metadata: Optional[dict[str, Any]] = None,
    user_id: Optional[uuid.UUID] = None,
) -> None:
    session.add(
        DocumentEvent(
            tenant_id=tenant_id,
            document_type=document_type,
            document_id=document_id,
            event_type=event_type,
            from_status=from_status,
            to_status=to_status,
            user_id=user_id,
            event_metadata=event_metadata,
        )
    )

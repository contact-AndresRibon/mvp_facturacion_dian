import uuid
from typing import Any, Optional

from sqlmodel import Session

from app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    def log(
        session: Session,
        *,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            request_id=request_id,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry

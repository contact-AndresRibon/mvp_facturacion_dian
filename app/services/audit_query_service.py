from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Session, func, select

from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.schemas.common import PaginatedResponse


class AuditQueryService:
    @staticmethod
    def list_logs(
        session: Session,
        user: User,
        *,
        resource_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResponse[AuditLogResponse]:
        base = select(AuditLog).where(AuditLog.tenant_id == user.tenant_id)
        if resource_type:
            base = base.where(AuditLog.resource_type == resource_type)
        if date_from:
            base = base.where(AuditLog.created_at >= date_from)
        if date_to:
            base = base.where(AuditLog.created_at <= date_to)

        total = session.exec(
            select(func.count()).select_from(base.subquery())
        ).one()
        items = session.exec(
            base.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        ).all()
        return PaginatedResponse(
            items=[AuditLogResponse.model_validate(a) for a in items],
            total=total,
            limit=limit,
            offset=offset,
        )

from datetime import datetime
from typing import Optional

from fastapi import APIRouter

from app.core.deps import AdminUserDep, SessionDep
from app.schemas.audit import AuditLogResponse
from app.schemas.common import PaginatedResponse
from app.services.audit_query_service import AuditQueryService

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_logs(
    session: SessionDep,
    user: AdminUserDep,
    resource_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedResponse[AuditLogResponse]:
    return AuditQueryService.list_logs(
        session,
        user,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

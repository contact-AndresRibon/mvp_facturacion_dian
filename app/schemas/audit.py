from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.schemas.common import ORMBase


class AuditLogResponse(ORMBase):
    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    request_id: Optional[str]
    details: Optional[dict[str, Any]]
    created_at: datetime

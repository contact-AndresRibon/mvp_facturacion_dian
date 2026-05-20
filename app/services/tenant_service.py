from uuid import UUID

from sqlmodel import Session

from app.audit.service import AuditService
from app.core.exceptions import NotFoundError
from app.models.tenant import Tenant, utc_now
from app.models.user import User
from app.schemas.tenant import TenantResponse, TenantUpdate


class TenantService:
    @staticmethod
    def get_my_tenant(session: Session, user: User) -> TenantResponse:
        tenant = session.get(Tenant, user.tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        return TenantResponse.model_validate(tenant)

    @staticmethod
    def update_my_tenant(
        session: Session,
        user: User,
        data: TenantUpdate,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> TenantResponse:
        tenant = session.get(Tenant, user.tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tenant, key, value)
        tenant.updated_at = utc_now()
        session.add(tenant)
        session.commit()
        session.refresh(tenant)

        AuditService.log(
            session,
            tenant_id=tenant.id,
            user_id=user.id,
            action="TENANT_UPDATED",
            resource_type="tenant",
            resource_id=str(tenant.id),
            details=update_data,
            ip_address=ip_address,
            request_id=request_id,
        )
        return TenantResponse.model_validate(tenant)

from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep, RequestIdDep, SessionDep, get_client_ip
from app.schemas.tenant import TenantResponse, TenantUpdate
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/me", response_model=TenantResponse)
def get_my_tenant(session: SessionDep, user: CurrentUserDep) -> TenantResponse:
    return TenantService.get_my_tenant(session, user)


@router.patch("/me", response_model=TenantResponse)
def update_my_tenant(
    data: TenantUpdate,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> TenantResponse:
    return TenantService.update_my_tenant(
        session,
        user,
        data,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )

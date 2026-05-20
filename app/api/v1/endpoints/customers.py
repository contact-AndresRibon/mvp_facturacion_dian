from uuid import UUID

from fastapi import APIRouter, Request, status

from app.core.deps import CurrentUserDep, RequestIdDep, SessionDep, get_client_ip
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=PaginatedResponse[CustomerResponse])
def list_customers(
    session: SessionDep,
    user: CurrentUserDep,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedResponse[CustomerResponse]:
    return CustomerService.list_customers(session, user, limit=limit, offset=offset)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    data: CustomerCreate,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> CustomerResponse:
    return CustomerService.create(
        session, user, data, ip_address=get_client_ip(request), request_id=request_id
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID, session: SessionDep, user: CurrentUserDep
) -> CustomerResponse:
    return CustomerService.get(session, user, customer_id)


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    data: CustomerUpdate,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> CustomerResponse:
    return CustomerService.update(
        session,
        user,
        customer_id,
        data,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )


@router.delete("/{customer_id}", response_model=MessageResponse)
def delete_customer(
    customer_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> MessageResponse:
    CustomerService.delete(
        session,
        user,
        customer_id,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )
    return MessageResponse(message="Customer deactivated")

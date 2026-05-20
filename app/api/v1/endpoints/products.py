from uuid import UUID

from fastapi import APIRouter, Request, status

from app.core.deps import CurrentUserDep, RequestIdDep, SessionDep, get_client_ip
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedResponse[ProductResponse])
def list_products(
    session: SessionDep,
    user: CurrentUserDep,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedResponse[ProductResponse]:
    return ProductService.list_products(session, user, limit=limit, offset=offset)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> ProductResponse:
    return ProductService.create(
        session, user, data, ip_address=get_client_ip(request), request_id=request_id
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID, session: SessionDep, user: CurrentUserDep
) -> ProductResponse:
    return ProductService.get(session, user, product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    data: ProductUpdate,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> ProductResponse:
    return ProductService.update(
        session,
        user,
        product_id,
        data,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )


@router.delete("/{product_id}", response_model=MessageResponse)
def delete_product(
    product_id: UUID,
    session: SessionDep,
    user: CurrentUserDep,
    request: Request,
    request_id: RequestIdDep,
) -> MessageResponse:
    ProductService.delete(
        session,
        user,
        product_id,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )
    return MessageResponse(message="Product deactivated")

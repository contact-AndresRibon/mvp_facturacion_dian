from uuid import UUID

from sqlmodel import Session, func, select

from app.audit.service import AuditService
from app.core.exceptions import NotFoundError
from app.models.product import Product, utc_now
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate


class ProductService:
    @staticmethod
    def list_products(
        session: Session, user: User, *, limit: int = 50, offset: int = 0
    ) -> PaginatedResponse[ProductResponse]:
        base = select(Product).where(Product.tenant_id == user.tenant_id)
        total = session.exec(
            select(func.count()).select_from(base.subquery())
        ).one()
        items = session.exec(base.offset(offset).limit(limit)).all()
        return PaginatedResponse(
            items=[ProductResponse.model_validate(p) for p in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def create(
        session: Session,
        user: User,
        data: ProductCreate,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> ProductResponse:
        product = Product(tenant_id=user.tenant_id, **data.model_dump())
        session.add(product)
        session.commit()
        session.refresh(product)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="PRODUCT_CREATED",
            resource_type="product",
            resource_id=str(product.id),
            ip_address=ip_address,
            request_id=request_id,
        )
        return ProductResponse.model_validate(product)

    @staticmethod
    def get(session: Session, user: User, product_id: UUID) -> ProductResponse:
        return ProductResponse.model_validate(
            ProductService._get_or_404(session, user, product_id)
        )

    @staticmethod
    def update(
        session: Session,
        user: User,
        product_id: UUID,
        data: ProductUpdate,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> ProductResponse:
        product = ProductService._get_or_404(session, user, product_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(product, key, value)
        product.updated_at = utc_now()
        session.add(product)
        session.commit()
        session.refresh(product)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="PRODUCT_UPDATED",
            resource_type="product",
            resource_id=str(product.id),
            ip_address=ip_address,
            request_id=request_id,
        )
        return ProductResponse.model_validate(product)

    @staticmethod
    def delete(
        session: Session,
        user: User,
        product_id: UUID,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> None:
        product = ProductService._get_or_404(session, user, product_id)
        product.is_active = False
        product.updated_at = utc_now()
        session.add(product)
        session.commit()

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="PRODUCT_DEACTIVATED",
            resource_type="product",
            resource_id=str(product.id),
            ip_address=ip_address,
            request_id=request_id,
        )

    @staticmethod
    def _get_or_404(session: Session, user: User, product_id: UUID) -> Product:
        product = session.get(Product, product_id)
        if not product or product.tenant_id != user.tenant_id:
            raise NotFoundError("Product not found")
        return product

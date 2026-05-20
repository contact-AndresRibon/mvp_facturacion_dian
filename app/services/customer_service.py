from uuid import UUID

from sqlmodel import Session, func, select

from app.audit.service import AuditService
from app.core.exceptions import NotFoundError
from app.models.customer import Customer, utc_now
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate


class CustomerService:
    @staticmethod
    def list_customers(
        session: Session, user: User, *, limit: int = 50, offset: int = 0
    ) -> PaginatedResponse[CustomerResponse]:
        base = select(Customer).where(Customer.tenant_id == user.tenant_id)
        total = session.exec(
            select(func.count()).select_from(base.subquery())
        ).one()
        items = session.exec(base.offset(offset).limit(limit)).all()
        return PaginatedResponse(
            items=[CustomerResponse.model_validate(c) for c in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def create(
        session: Session,
        user: User,
        data: CustomerCreate,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> CustomerResponse:
        customer = Customer(tenant_id=user.tenant_id, **data.model_dump())
        session.add(customer)
        session.commit()
        session.refresh(customer)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="CUSTOMER_CREATED",
            resource_type="customer",
            resource_id=str(customer.id),
            ip_address=ip_address,
            request_id=request_id,
        )
        return CustomerResponse.model_validate(customer)

    @staticmethod
    def get(session: Session, user: User, customer_id: UUID) -> CustomerResponse:
        customer = CustomerService._get_or_404(session, user, customer_id)
        return CustomerResponse.model_validate(customer)

    @staticmethod
    def update(
        session: Session,
        user: User,
        customer_id: UUID,
        data: CustomerUpdate,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> CustomerResponse:
        customer = CustomerService._get_or_404(session, user, customer_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(customer, key, value)
        customer.updated_at = utc_now()
        session.add(customer)
        session.commit()
        session.refresh(customer)

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="CUSTOMER_UPDATED",
            resource_type="customer",
            resource_id=str(customer.id),
            ip_address=ip_address,
            request_id=request_id,
        )
        return CustomerResponse.model_validate(customer)

    @staticmethod
    def delete(
        session: Session,
        user: User,
        customer_id: UUID,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> None:
        customer = CustomerService._get_or_404(session, user, customer_id)
        customer.is_active = False
        customer.updated_at = utc_now()
        session.add(customer)
        session.commit()

        AuditService.log(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="CUSTOMER_DEACTIVATED",
            resource_type="customer",
            resource_id=str(customer.id),
            ip_address=ip_address,
            request_id=request_id,
        )

    @staticmethod
    def _get_or_404(session: Session, user: User, customer_id: UUID) -> Customer:
        customer = session.get(Customer, customer_id)
        if not customer or customer.tenant_id != user.tenant_id:
            raise NotFoundError("Customer not found")
        return customer

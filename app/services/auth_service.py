from sqlmodel import Session, select

from app.audit.service import AuditService
from app.core.config import get_settings
from app.core.exceptions import AppError, ForbiddenError
from app.core.security import create_access_token, get_password_hash, verify_password
from app.domain.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse


class AuthService:
    @staticmethod
    def register(
        session: Session,
        data: RegisterRequest,
        *,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> tuple[Tenant, User, TokenResponse]:
        settings = get_settings()
        if not settings.allow_public_register:
            raise ForbiddenError("Public registration is disabled")

        existing = session.exec(
            select(User).where(User.email == data.admin_email)
        ).first()
        if existing:
            raise AppError("Email already registered", status_code=409, code="email_exists")

        tenant = Tenant(
            legal_name=data.legal_name,
            trade_name=data.trade_name,
            nit=data.nit,
            dv=data.dv,
            email=data.email,
            address=data.address,
        )
        session.add(tenant)
        session.flush()

        user = User(
            tenant_id=tenant.id,
            email=data.admin_email,
            hashed_password=get_password_hash(data.admin_password),
            full_name=data.admin_full_name,
            role=UserRole.ADMIN,
        )
        session.add(user)
        session.commit()
        session.refresh(tenant)
        session.refresh(user)

        AuditService.log(
            session,
            tenant_id=tenant.id,
            user_id=user.id,
            action="TENANT_REGISTERED",
            resource_type="tenant",
            resource_id=str(tenant.id),
            details={"nit": tenant.nit},
            ip_address=ip_address,
            request_id=request_id,
        )

        token = create_access_token(
            user_id=user.id, tenant_id=tenant.id, role=user.role.value
        )
        return tenant, user, TokenResponse(access_token=token)

    @staticmethod
    def login(session: Session, email: str, password: str) -> TokenResponse:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or not verify_password(password, user.hashed_password):
            raise AppError("Invalid credentials", status_code=401, code="invalid_credentials")
        if not user.is_active:
            raise ForbiddenError("User is inactive")

        token = create_access_token(
            user_id=user.id, tenant_id=user.tenant_id, role=user.role.value
        )
        return TokenResponse(access_token=token)

    @staticmethod
    def me(user: User) -> UserResponse:
        return UserResponse.model_validate(user)

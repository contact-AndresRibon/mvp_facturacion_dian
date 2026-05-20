import uuid
from typing import Annotated, Optional

from fastapi import Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.domain.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SessionDep = Annotated[Session, Depends(get_session)]


def get_request_id(
    x_request_id: Annotated[Optional[str], Header(alias="X-Request-ID")] = None,
) -> str:
    return x_request_id or str(uuid.uuid4())


RequestIdDep = Annotated[str, Depends(get_request_id)]


async def get_current_user(
    session: SessionDep,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise ForbiddenError("Could not validate credentials") from exc

    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise ForbiddenError("Inactive or unknown user")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUserDep) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin role required")
    return user


AdminUserDep = Annotated[User, Depends(require_admin)]


def get_client_ip(request: Request) -> Optional[str]:
    if request.client:
        return request.client.host
    return None

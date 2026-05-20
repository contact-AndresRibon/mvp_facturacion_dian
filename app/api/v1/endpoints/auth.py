from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.core.deps import CurrentUserDep, RequestIdDep, SessionDep, get_client_ip
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    data: RegisterRequest,
    session: SessionDep,
    request: Request,
    request_id: RequestIdDep,
) -> TokenResponse:
    _, _, token = AuthService.register(
        session,
        data,
        ip_address=get_client_ip(request),
        request_id=request_id,
    )
    return token


@router.post("/login", response_model=TokenResponse)
def login(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    return AuthService.login(session, form_data.username, form_data.password)


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUserDep) -> UserResponse:
    return AuthService.me(user)

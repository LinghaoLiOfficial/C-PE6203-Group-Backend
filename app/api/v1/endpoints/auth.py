from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_active_user, get_db, require_admin
from app.models.user import User
from app.schemas.auth import (
    AdminUserUpdateRequest,
    AuthTokenPairResponse,
    LoginRequest,
    RegisterRequest,
    SendEmailVerificationRequest,
    SendEmailVerificationResponse,
    ProfileUpdateRequest,
    UpdateMeRequest,
    UserRead,
)
from app.services.auth_service import AuthService, UserService

router = APIRouter(prefix="/auth")
profile_router = APIRouter()
admin_router = APIRouter(prefix="/admin/users")
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.post("/email-verification-codes", response_model=SendEmailVerificationResponse)
def send_email_verification_code(
    db: DbSession,
    payload: SendEmailVerificationRequest,
) -> SendEmailVerificationResponse:
    return AuthService(db).send_register_code(str(payload.email))


@router.post("/register/code", response_model=SendEmailVerificationResponse)
def send_register_code(
    db: DbSession,
    payload: SendEmailVerificationRequest,
) -> SendEmailVerificationResponse:
    return send_email_verification_code(db, payload)


@router.post("/register", response_model=AuthTokenPairResponse, status_code=status.HTTP_201_CREATED)
def register(db: DbSession, payload: RegisterRequest) -> AuthTokenPairResponse:
    return AuthService(db).register(payload)


@router.post("/login", response_model=AuthTokenPairResponse)
def login(db: DbSession, payload: LoginRequest) -> AuthTokenPairResponse:
    return AuthService(db).login(payload)


@router.post("/refresh", response_model=AuthTokenPairResponse)
def refresh(db: DbSession, authorization: Annotated[str | None, Header(alias="Authorization")] = None) -> AuthTokenPairResponse:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please sign in first.")
    return AuthService(db).refresh(authorization.removeprefix("Bearer ").strip())


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(db: DbSession, current_user: CurrentUser) -> Response:
    AuthService(db).logout(current_user)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    return response


@router.get("/me", response_model=UserRead)
def get_me(db: DbSession, current_user: CurrentUser) -> UserRead:
    return AuthService(db).get_me(current_user)


@profile_router.patch("/me/profile", response_model=UserRead)
def update_me_profile(db: DbSession, current_user: CurrentUser, payload: ProfileUpdateRequest) -> UserRead:
    return AuthService(db).update_profile(current_user, payload)


@profile_router.patch("/me", response_model=UserRead)
def update_me(db: DbSession, current_user: CurrentUser, payload: UpdateMeRequest) -> UserRead:
    return AuthService(db).update_me(current_user, payload)


@admin_router.get("", response_model=list[UserRead])
def list_users(db: DbSession, _: AdminUser) -> list[UserRead]:
    return UserService(db).list_users()


@admin_router.get("/{user_id}", response_model=UserRead)
def get_user(db: DbSession, _: AdminUser, user_id: UUID) -> UserRead:
    return UserService(db).get_user(user_id, require_manageable=True)


@admin_router.patch("/{user_id}", response_model=UserRead)
def update_user(
    db: DbSession,
    _: AdminUser,
    user_id: UUID,
    payload: AdminUserUpdateRequest,
) -> UserRead:
    return UserService(db).update_user(user_id, payload)

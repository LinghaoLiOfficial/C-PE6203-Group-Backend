from __future__ import annotations

import logging
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_verification_code,
    hash_password,
    hash_verification_code,
    make_avatar_color,
    make_avatar_seed,
    validate_password_strength,
    verify_password,
    verify_verification_code,
)
from app.models.applicant_profile import ApplicantProfile
from app.models.email_verification_code import EmailVerificationCode
from app.models.user import User
from app.schemas.auth import (
    AdminUserUpdateRequest,
    LoginRequest,
    ProfileRead,
    ProfileUpdateRequest,
    RegisterRequest,
    SendEmailVerificationResponse,
    TokenPairResponse,
    UpdateMeRequest,
    UserRead,
)

logger = logging.getLogger(__name__)
REGISTER_PURPOSE = "register"
MAX_VERIFICATION_ATTEMPTS = 5
MANAGEABLE_ROLES = {"user"}


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def send_register_code(self, email: str) -> SendEmailVerificationResponse:
        normalized_email = _normalize_email(email)
        self._ensure_email_available(normalized_email)
        self._ensure_can_resend(normalized_email)

        code = generate_verification_code()
        delivery_channel = "email" if settings.smtp_configured else "dev_log"
        verification = EmailVerificationCode(
            email=normalized_email,
            code_hash=hash_verification_code(normalized_email, code),
            purpose=REGISTER_PURPOSE,
            expires_at=datetime.now(UTC)
            + timedelta(minutes=settings.email_verification_expire_minutes),
        )
        self.db.add(verification)
        self.db.flush()
        try:
            self._send_email_code(normalized_email, code)
        except (smtplib.SMTPException, OSError) as exc:
            self.db.rollback()
            logger.exception("Failed to send verification email to %s", normalized_email)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Verification email failed to send. Please check the SMTP app password, sender address, and whether QQ Mail SMTP is enabled.",
            ) from exc
        self.db.commit()
        return SendEmailVerificationResponse(
            message="Verification code sent to your email." if delivery_channel == "email" else "Verification code stored in backend logs.",
            expires_in_minutes=settings.email_verification_expire_minutes,
            resend_after_seconds=settings.email_verification_resend_seconds,
            delivery_channel=delivery_channel,
        )

    def register(self, payload: RegisterRequest) -> TokenPairResponse:
        normalized_email = _normalize_email(str(payload.email))
        username = _normalize_username(payload.username)
        try:
            validate_password_strength(payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        self._ensure_email_available(normalized_email)
        self._ensure_username_available(username)
        self._consume_verification_code(normalized_email, payload.verification_code)

        user = User(
            email=normalized_email,
            username=username,
            password_hash=hash_password(payload.password),
            display_name=None,
            role="user",
            is_active=True,
            is_email_verified=True,
            avatar_seed=make_avatar_seed(username),
            avatar_bg_color=make_avatar_color(f"{normalized_email}:{username}"),
        )
        self.db.add(user)
        self._commit_unique_user_change()
        self.db.refresh(user)
        self._ensure_profile_exists(user)
        return self._issue_tokens(user)

    def login(self, payload: LoginRequest) -> TokenPairResponse:
        user = self.db.scalar(select(User).where(User.email == _normalize_email(payload.email)))
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This user account is disabled.")
        user.last_login_at = datetime.now(UTC)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return self._issue_tokens(user)

    def refresh(self, refresh_token: str) -> TokenPairResponse:
        user_id, role, version = decode_refresh_token(refresh_token)
        user = self.db.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid.")
        if user.role != role or user.refresh_token_version != version:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has expired.")
        return self._issue_tokens(user)

    def update_profile(self, user: User, payload: ProfileUpdateRequest) -> UserRead:
        profile = self._get_or_create_profile(user)
        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(profile, key, value)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        self.db.refresh(user)
        return self._serialize_user(user, profile)

    def update_me(self, user: User, payload: UpdateMeRequest) -> User:
        updates = payload.model_dump(exclude_unset=True)
        if "username" in updates and updates["username"] is not None:
            username = _normalize_username(updates["username"])
            self._ensure_username_available(username, exclude_user_id=user.id)
            user.username = username
            user.avatar_seed = make_avatar_seed(username)
        if "display_name" in updates:
            user.display_name = _normalize_optional_text(updates["display_name"])
        self.db.add(user)
        self._commit_unique_user_change()
        self.db.refresh(user)
        return user

    def get_me(self, user: User) -> UserRead:
        profile = self._get_or_create_profile(user)
        return self._serialize_user(user, profile)

    def logout(self, user: User) -> None:
        user.refresh_token_version += 1
        self.db.add(user)
        self.db.commit()

    def _issue_tokens(self, user: User) -> TokenPairResponse:
        profile = self._get_or_create_profile(user)
        access_token, access_expires_at = create_access_token(
            user.id, role=user.role, version=user.refresh_token_version
        )
        refresh_token, refresh_expires_at = create_refresh_token(
            user.id, role=user.role, version=user.refresh_token_version
        )
        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            user=self._serialize_user(user, profile),
        )

    def _ensure_profile_exists(self, user: User) -> None:
        profile = self.db.get(ApplicantProfile, user.id)
        if profile is not None:
            return
        first_name = user.display_name or user.username
        last_name = user.username or user.display_name or "User"
        profile = ApplicantProfile(
            user_id=user.id,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            years_experience=0,
            employment_status="unemployed",
        )
        self.db.add(profile)
        self.db.commit()

    def _get_or_create_profile(self, user: User) -> ApplicantProfile:
        profile = self.db.get(ApplicantProfile, user.id)
        if profile is None:
            profile = ApplicantProfile(
                user_id=user.id,
                first_name=user.display_name or user.username,
                last_name=user.username,
                years_experience=0,
                employment_status="unemployed",
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def _serialize_user(self, user: User, profile: ApplicantProfile | None = None) -> UserRead:
        if profile is None:
            profile = self._get_or_create_profile(user)
        return UserRead(
            id=user.id,
            email=user.email,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
            avatar_seed=user.avatar_seed,
            avatar_bg_color=user.avatar_bg_color,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            profile=ProfileRead.model_validate(profile),
        )

    def _ensure_email_available(self, email: str) -> None:
        if self.db.scalar(select(User.id).where(User.email == email)) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered.")

    def _ensure_username_available(
        self, username: str, exclude_user_id: UUID | None = None
    ) -> None:
        statement = select(User.id).where(User.username == username)
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)
        if self.db.scalar(statement) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

    def _ensure_can_resend(self, email: str) -> None:
        latest = self.db.scalar(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == email,
                EmailVerificationCode.purpose == REGISTER_PURPOSE,
            )
            .order_by(EmailVerificationCode.created_at.desc())
            .limit(1)
        )
        if latest is None:
            return
        elapsed = datetime.now(UTC) - latest.created_at
        if elapsed.total_seconds() < settings.email_verification_resend_seconds:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Verification code requests are too frequent. Please try again later.",
            )

    def _consume_verification_code(self, email: str, code: str) -> None:
        verification = self.db.scalar(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == email,
                EmailVerificationCode.purpose == REGISTER_PURPOSE,
                EmailVerificationCode.consumed_at.is_(None),
            )
            .order_by(EmailVerificationCode.created_at.desc())
            .limit(1)
        )
        if verification is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code is invalid or expired.")
        now = datetime.now(UTC)
        if verification.expires_at <= now:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification code is invalid or expired.")
        if verification.attempt_count >= MAX_VERIFICATION_ATTEMPTS:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many verification code attempts.")
        verification.attempt_count += 1
        if not verify_verification_code(email, code, verification.code_hash):
            self.db.add(verification)
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect verification code.")
        verification.consumed_at = now
        self.db.add(verification)
        self.db.flush()

    def _send_email_code(self, email: str, code: str) -> None:
        if not settings.smtp_configured:
            logger.info("email_verification.dev_code email=%s code=%s", email, code)
            return
        message = EmailMessage()
        message["Subject"] = "Email verification code"
        message["From"] = settings.smtp_sender_email or ""
        message["To"] = email
        message.set_content(
            f"Your verification code is {code}. It is valid for {settings.email_verification_expire_minutes} minutes."
        )
        smtp_class = smtplib.SMTP_SSL if settings.smtp_port == 465 else smtplib.SMTP
        with smtp_class(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_use_tls and settings.smtp_port != 465:
                smtp.starttls()
            if settings.smtp_login_username and settings.smtp_code:
                smtp.login(settings.smtp_login_username, settings.smtp_code)
            smtp.send_message(message)

    def _commit_unique_user_change(self) -> None:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or username already exists.",
            ) from exc


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_users(self) -> list[User]:
        return list(self.db.scalars(select(User).where(User.role != "admin").order_by(User.created_at.desc())))

    def get_user(self, user_id: UUID, *, require_manageable: bool = False) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        if require_manageable:
            self._ensure_manageable(user)
        return user

    def update_user(self, user_id: UUID, payload: AdminUserUpdateRequest) -> User:
        user = self.get_user(user_id)
        self._ensure_manageable(user)
        updates = payload.model_dump(exclude_unset=True)
        if "username" in updates and updates["username"] is not None:
            username = _normalize_username(updates["username"])
            AuthService(self.db)._ensure_username_available(username, exclude_user_id=user.id)
            user.username = username
            user.avatar_seed = make_avatar_seed(username)
        if "display_name" in updates:
            user.display_name = _normalize_optional_text(updates["display_name"])
        if "role" in updates and updates["role"] is not None:
            if updates["role"] not in MANAGEABLE_ROLES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role is not allowed.")
            user.role = updates["role"]
        if "is_active" in updates and updates["is_active"] is not None:
            user.is_active = updates["is_active"]
        self.db.add(user)
        AuthService(self.db)._commit_unique_user_change()
        self.db.refresh(user)
        return user

    def _ensure_manageable(self, user: User) -> None:
        if user.role == "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Other administrators cannot be managed.")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_username(username: str) -> str:
    normalized = username.strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username cannot be empty.")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None

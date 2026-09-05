from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

UserRole = Literal["user", "admin"]
ManageableUserRole = Literal["user"]


class SendEmailVerificationRequest(BaseModel):
    email: EmailStr


class SendEmailVerificationResponse(BaseModel):
    message: str
    expires_in_minutes: int
    resend_after_seconds: int
    delivery_channel: Literal["email", "dev_log"]


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    verification_code: str = Field(min_length=6, max_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class ProfileRead(BaseModel):
    first_name: str
    last_name: str
    years_experience: int
    current_company: str | None
    headline: str | None
    employment_status: str
    notice_period: str | None

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    display_name: str | None
    role: UserRole
    is_active: bool
    is_email_verified: bool
    avatar_seed: str
    avatar_bg_color: str
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    profile: ProfileRead | None = None

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    years_experience: int | None = Field(default=None, ge=0, le=50)
    current_company: str | None = Field(default=None, max_length=255)
    headline: str | None = Field(default=None, max_length=300)
    employment_status: str | None = Field(default=None, max_length=30)
    notice_period: str | None = Field(default=None, max_length=50)


class AdminUserUpdateRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    role: ManageableUserRole | None = None
    is_active: bool | None = None


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    refresh_expires_at: datetime
    user: UserRead


class AuthTokenPairResponse(TokenPairResponse):
    pass


class UpdateMeRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)

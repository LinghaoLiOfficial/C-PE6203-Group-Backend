from sqlalchemy import DDL, event

from app.db.base_class import Base
from app.models import (
    Application,
    ApplicantProfile,
    EmailVerificationCode,
    ExampleItem,
    Job,
    Notification,
    Resume,
    ResumeRewrite,
    User,
)

event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS vector"))

__all__ = [
    "Base",
    "Application",
    "ApplicantProfile",
    "EmailVerificationCode",
    "ExampleItem",
    "Job",
    "Notification",
    "Resume",
    "ResumeRewrite",
    "User",
]

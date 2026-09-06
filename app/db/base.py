from sqlalchemy import DDL, event

from app.db.base_class import Base
from app.models import (
    Application,
    ApplicantProfile,
    CandidateGraph,
    CandidateJobMatch,
    EmailVerificationCode,
    ExampleItem,
    FeedbackEvent,
    Job,
    JobImportBatch,
    JobImportRow,
    JobMarketProfile,
    Notification,
    Resume,
    ResumeParseTask,
    ResumeRewrite,
    ResumeTailoringTask,
    ResumeVariant,
    User,
)

event.listen(Base.metadata, "before_create", DDL("CREATE EXTENSION IF NOT EXISTS vector"))

__all__ = [
    "Base",
    "Application",
    "ApplicantProfile",
    "CandidateGraph",
    "CandidateJobMatch",
    "EmailVerificationCode",
    "ExampleItem",
    "FeedbackEvent",
    "Job",
    "JobImportBatch",
    "JobImportRow",
    "JobMarketProfile",
    "Notification",
    "Resume",
    "ResumeParseTask",
    "ResumeRewrite",
    "ResumeTailoringTask",
    "ResumeVariant",
    "User",
]

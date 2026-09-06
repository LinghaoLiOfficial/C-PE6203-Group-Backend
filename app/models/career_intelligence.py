from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base_class import Base


class CandidateGraph(Base):
    __tablename__ = "candidate_graphs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    skills: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    experience_highlights: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    experiences: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    education: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    projects: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    achievements: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    publications: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_spans: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    user_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )


class JobMarketProfile(Base):
    __tablename__ = "job_market_profiles"
    __table_args__ = (UniqueConstraint("job_id", name="uq_job_market_profiles_job_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    occupation_family: Mapped[str | None] = mapped_column(String(120), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(80), nullable=True)
    required_skills: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    preferred_skills: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    education_requirements: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    experience_requirements: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    licenses: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    salary_confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="C")
    freshness_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)
    raw_requirements: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )


class CandidateJobMatch(Base):
    __tablename__ = "candidate_job_matches"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_candidate_job_matches_user_job"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="stretch")
    score_vector: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fit_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rationale: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    transition_difficulty: Mapped[str] = mapped_column(String(40), nullable=False, default="moderate")
    data_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )


class FeedbackEvent(Base):
    __tablename__ = "feedback_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(UTC)
    )


class ResumeVariant(Base):
    __tablename__ = "resume_variants"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    job_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    claims: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    validation_results: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    resume_sections: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    change_summary: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    evidence_used: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    target_requirements: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    rewritten_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(UTC)
    )


class ResumeTailoringTask(Base):
    __tablename__ = "resume_tailoring_tasks"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    stage: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), default=lambda: datetime.now(UTC))

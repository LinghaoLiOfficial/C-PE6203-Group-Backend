from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse


class JobRead(BaseModel):
    id: UUID
    job_title: str
    job_description: str
    source_id: int | None = None
    company_name: str | None
    location: str | None
    city_location: str | None = None
    country_location: str | None = None
    pay_period: str | None = None
    mid_salary_sgd: float | None = None
    source: str
    external_id: str
    external_apply_url: str
    is_active: bool
    ingested_at: datetime
    match_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


class JobDetailRead(JobRead):
    skill_tags: list[str] | None = None


class ResumeRead(BaseModel):
    id: UUID
    user_id: UUID
    file_name: str
    file_url: str
    parsed_text: str | None
    extracted_skills: list[str] | None
    embedding_ready: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeUploadResponse(BaseModel):
    resume_id: UUID
    status: Literal["processing", "ready"]


class ApplicationRead(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID | None
    job_name_snapshot: str
    company_name_snapshot: str | None
    location_snapshot: str | None
    external_apply_url_snapshot: str
    status: str
    match_score: float
    applied_at: datetime
    updated_at: datetime
    job: JobRead | None = None

    model_config = ConfigDict(from_attributes=True)


class ApplicationCreateRequest(BaseModel):
    job_id: UUID


class ApplicationStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class NotificationRead(BaseModel):
    id: UUID
    user_id: UUID
    message: str
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationSummary(BaseModel):
    unread_count: int
    items: list[NotificationRead]


class DashboardSummary(BaseModel):
    resumes_total: int
    active_resume_exists: bool
    jobs_total: int
    jobs_matched: int
    applications_total: int
    unread_notifications: int


class JobSalaryRangeSummary(BaseModel):
    min: float | None
    max: float | None


class JobListSummary(BaseModel):
    jobs_total: int
    salary_range: JobSalaryRangeSummary


class PaginatedJobReadResponse(PaginatedResponse[JobRead]):
    summary: JobListSummary | None = None

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
    opportunity_score: float | None = None
    opportunity_category: str | None = None
    fit_breakdown: dict | None = None
    rationale: list[str] | None = None
    transition_difficulty: str | None = None
    data_confidence: float | None = None

    model_config = ConfigDict(from_attributes=True)


class JobDetailRead(JobRead):
    skill_tags: list[str] | None = None
    canonical_job_profile: dict | None = None
    requirement_summary: dict | None = None
    opportunity_explanation: dict | None = None


class ResumeRead(BaseModel):
    id: UUID
    user_id: UUID
    file_name: str
    file_url: str
    parsed_text: str | None
    extracted_skills: list[str] | None
    candidate_graph: dict | None = None
    embedding_ready: bool
    parse_status: Literal["uploaded", "queued", "running", "completed", "failed"]
    parse_progress: int = Field(ge=0, le=100)
    parse_stage: str
    parse_error: str | None = None
    parse_task_id: UUID | None = None
    parse_mode: str = "unknown"
    parse_diagnostics: dict | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResumeUploadResponse(BaseModel):
    resume_id: UUID
    status: Literal["uploaded"]


class ResumeParseTaskRead(BaseModel):
    id: UUID
    resume_id: UUID
    status: Literal["queued", "running", "completed", "failed"]
    stage: str
    progress: int = Field(ge=0, le=100)
    error_message: str | None = None
    diagnostics: dict | None = None
    attempts: int
    worker_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ResumeParseStatusRead(BaseModel):
    resume_id: UUID
    task: ResumeParseTaskRead | None = None


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


class OpportunitySection(BaseModel):
    title: str
    jobs: list[JobRead]


class OpportunityMapRead(BaseModel):
    overview: DashboardSummary | None = None
    sections: list[OpportunitySection]
    score_vector: dict | None = None


class ResumeGraphRead(BaseModel):
    candidate_graph: dict | None
    resume: ResumeRead
    resume_variant: dict | None = None


class OpportunityVectorRead(BaseModel):
    salary_advantage: float = 0.0
    attainability: float = 0.0
    demand: float = 0.0
    entry_barrier: float = 0.0
    career_option: float = 0.0
    preference_fit: float = 0.0
    data_confidence: float = 0.0
    fit: float = 0.0


class FeedbackCreateRequest(BaseModel):
    job_id: UUID | None = None
    event_type: str = Field(min_length=1, max_length=40)
    payload: dict | None = None


class FeedbackRead(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID | None
    event_type: str
    payload: dict | None
    created_at: datetime


class CandidateProfileRead(BaseModel):
    user_id: UUID
    profile: dict
    preferences: dict
    constraints: dict
    confirmed: bool


class CandidateProfileUpdateRequest(BaseModel):
    profile: dict = Field(default_factory=dict)
    preferences: dict = Field(default_factory=dict)
    constraints: dict = Field(default_factory=dict)
    confirmed: bool = False


class JobSalaryRangeSummary(BaseModel):
    min: float | None
    max: float | None


class JobListSummary(BaseModel):
    jobs_total: int
    salary_range: JobSalaryRangeSummary


class PaginatedJobReadResponse(PaginatedResponse[JobRead]):
    summary: JobListSummary | None = None


class JobImportRowRead(BaseModel):
    row_number: int
    status: str
    dedupe_key: str | None = None
    error_message: str | None = None
    raw_payload: dict | None = None
    normalized_payload: dict | None = None
    canonical_job_profile: dict | None = None
    job_id: UUID | None = None


class JobImportBatchRead(BaseModel):
    id: UUID
    admin_user_id: UUID
    file_name: str
    status: str
    total_rows: int
    pending_insert_rows: int
    pending_update_rows: int
    duplicate_rows: int
    error_rows: int
    inserted_rows: int
    updated_rows: int
    skipped_rows: int
    source: str
    created_at: datetime
    imported_at: datetime | None
    rows: list[JobImportRowRead] = Field(default_factory=list)


class JobImportPreviewResponse(BaseModel):
    batch: JobImportBatchRead


class JobImportConfirmRequest(BaseModel):
    batch_id: UUID


class JobImportConfirmResponse(BaseModel):
    batch: JobImportBatchRead


class JobImportHistoryItem(BaseModel):
    id: UUID
    file_name: str
    status: str
    total_rows: int
    inserted_rows: int
    updated_rows: int
    skipped_rows: int
    error_rows: int
    created_at: datetime
    imported_at: datetime | None


class JobImportHistoryResponse(BaseModel):
    items: list[JobImportHistoryItem]


class ResumeVariantRead(BaseModel):
    rewritten_text: str
    cached: bool
    plan: dict | None = None
    claims: list[dict] | None = None
    validation_results: list[dict] | None = None
    target_job_profile: dict | None = None
    resume_sections: dict = Field(default_factory=dict)
    change_summary: list[dict] = Field(default_factory=list)
    evidence_used: list[dict] = Field(default_factory=list)
    target_requirements: list[dict] = Field(default_factory=list)


class ResumeTailoringTaskCreateRead(BaseModel):
    id: UUID
    user_id: UUID
    resume_id: UUID
    job_id: UUID
    job_title: str | None = None
    company_name: str | None = None
    source_file_name: str | None = None
    status: str
    stage: str
    progress: int
    error_message: str | None = None
    attempts: int
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None


class ResumeTailoringTaskRead(BaseModel):
    id: UUID
    user_id: UUID
    resume_id: UUID
    job_id: UUID
    job_title: str | None = None
    company_name: str | None = None
    source_file_name: str | None = None
    status: str
    stage: str
    progress: int
    error_message: str | None = None
    attempts: int
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    variant: dict | None = None


class TailoredResumeListItem(ResumeTailoringTaskRead):
    """The latest tailoring task for one target job, including its latest result."""


class ResumeVariantListRead(BaseModel):
    id: UUID
    user_id: UUID
    resume_id: UUID | None
    job_id: UUID
    job_title: str | None = None
    company_name: str | None = None
    source_file_name: str | None = None
    rewritten_text: str
    resume_sections: dict = Field(default_factory=dict)
    change_summary: list[dict] = Field(default_factory=list)
    evidence_used: list[dict] = Field(default_factory=list)
    target_requirements: list[dict] = Field(default_factory=list)
    cached: bool = True
    plan: dict | None = None
    claims: list[dict] | None = None
    validation_results: list[dict] | None = None
    target_job_profile: dict | None = None
    created_at: datetime

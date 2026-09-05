from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_active_user, get_db, require_admin
from app.models.user import User
from app.schemas.auth import UserRead
from app.schemas.portal import (
    ApplicationCreateRequest,
    ApplicationRead,
    ApplicationStatusUpdateRequest,
    DashboardSummary,
    JobDetailRead,
    PaginatedJobReadResponse,
    JobRead,
    NotificationRead,
    NotificationSummary,
    ResumeRead,
    ResumeUploadResponse,
)
from app.services.job_portal_service import JobPortalService

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: DbSession, current_user: CurrentUser) -> DashboardSummary:
    return DashboardSummary(**JobPortalService(db).dashboard_summary(current_user.id))


@router.post("/resumes", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_resume(db: DbSession, current_user: CurrentUser, file: UploadFile = File(...)) -> ResumeUploadResponse:
    resume = JobPortalService(db).upload_resume(current_user.id, file)
    return ResumeUploadResponse(resume_id=resume["id"], status="ready" if resume["embedding_ready"] else "processing")


@router.get("/resumes", response_model=list[ResumeRead])
def list_resumes(db: DbSession, current_user: CurrentUser) -> list[ResumeRead]:
    return [ResumeRead(**item) for item in JobPortalService(db).list_resumes(current_user.id)]


@router.get("/resumes/{resume_id}/parsed", response_model=ResumeRead)
def get_resume(db: DbSession, current_user: CurrentUser, resume_id: UUID) -> ResumeRead:
    return ResumeRead(**JobPortalService(db).get_resume(current_user.id, resume_id))


@router.delete("/resumes/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(db: DbSession, current_user: CurrentUser, resume_id: UUID) -> None:
    JobPortalService(db).delete_resume(current_user.id, resume_id)


@router.get("/jobs", response_model=PaginatedJobReadResponse)
def list_jobs(
    db: DbSession,
    current_user: CurrentUser,
    page: int = 1,
    limit: int = 20,
    location: str | None = None,
    skills: str | None = None,
    company: str | None = None,
) -> PaginatedJobReadResponse:
    return JobPortalService(db).list_jobs(
        current_user.id, page=page, limit=limit, location=location, skills=skills, company=company
    )


@router.get("/jobs/{job_id}", response_model=JobDetailRead)
def get_job(db: DbSession, current_user: CurrentUser, job_id: UUID) -> JobDetailRead:
    return JobDetailRead(**JobPortalService(db).get_job(current_user.id, job_id))


@router.post("/jobs/{job_id}/rewrite")
def rewrite_job(db: DbSession, current_user: CurrentUser, job_id: UUID) -> dict:
    return JobPortalService(db).rewrite_job_resume(current_user.id, job_id)


@router.post("/applications", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_application(db: DbSession, current_user: CurrentUser, payload: ApplicationCreateRequest) -> dict:
    return JobPortalService(db).create_application(current_user.id, payload.job_id)


@router.get("/applications", response_model=list[ApplicationRead])
def list_applications(db: DbSession, current_user: CurrentUser) -> list[ApplicationRead]:
    return [ApplicationRead(**item) for item in JobPortalService(db).list_applications(current_user.id)]


@router.patch("/applications/{application_id}", response_model=ApplicationRead)
def update_application(
    db: DbSession, current_user: CurrentUser, application_id: UUID, payload: ApplicationStatusUpdateRequest
) -> ApplicationRead:
    return ApplicationRead(
        **JobPortalService(db).update_application_status(current_user.id, application_id, payload.status)
    )


@router.get("/notifications", response_model=NotificationSummary)
def list_notifications(db: DbSession, current_user: CurrentUser) -> NotificationSummary:
    payload = JobPortalService(db).list_notifications(current_user.id)
    return NotificationSummary(
        unread_count=payload["unread_count"],
        items=[NotificationRead(**item) for item in payload["items"]],
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(db: DbSession, current_user: CurrentUser, notification_id: UUID) -> NotificationRead:
    return NotificationRead(
        **JobPortalService(db).mark_notification_read(current_user.id, notification_id)
    )


@router.post("/admin/ingest/run", status_code=status.HTTP_202_ACCEPTED)
def run_ingest(db: DbSession, _: AdminUser) -> dict:
    return JobPortalService(db).ingest_jobs()

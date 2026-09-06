from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_active_user, get_db, require_admin
from app.models.user import User
from app.schemas.portal import (
    ApplicationCreateRequest,
    ApplicationRead,
    ApplicationStatusUpdateRequest,
    CandidateProfileRead,
    CandidateProfileUpdateRequest,
    DashboardSummary,
    FeedbackCreateRequest,
    FeedbackRead,
    JobDetailRead,
    JobImportConfirmRequest,
    JobImportConfirmResponse,
    JobImportHistoryResponse,
    JobImportPreviewResponse,
    NotificationRead,
    NotificationSummary,
    OpportunityMapRead,
    PaginatedJobReadResponse,
    ResumeVariantListRead,
    ResumeTailoringTaskCreateRead,
    TailoredResumeListItem,
    ResumeTailoringTaskRead,
    ResumeGraphRead,
    ResumeParseStatusRead,
    ResumeParseTaskRead,
    ResumeRead,
    ResumeUploadResponse,
)
from app.services.job_import_service import JobImportService
from app.services.job_portal_service import JobPortalService

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]
ResumeUploadFile = Annotated[UploadFile, File(...)]


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: DbSession, current_user: CurrentUser) -> DashboardSummary:
    return DashboardSummary(**JobPortalService(db).dashboard_summary(current_user.id))


@router.get("/candidate/profile", response_model=CandidateProfileRead)
def candidate_profile(db: DbSession, current_user: CurrentUser) -> CandidateProfileRead:
    return CandidateProfileRead(**JobPortalService(db).get_candidate_profile(current_user.id))


@router.patch("/candidate/profile", response_model=CandidateProfileRead)
def update_candidate_profile(
    db: DbSession, current_user: CurrentUser, payload: CandidateProfileUpdateRequest
) -> CandidateProfileRead:
    return CandidateProfileRead(
        **JobPortalService(db).update_candidate_profile(current_user.id, payload)
    )


@router.post("/resumes", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_resume(
    db: DbSession, current_user: CurrentUser, file: ResumeUploadFile
) -> ResumeUploadResponse:
    resume = JobPortalService(db).upload_resume(current_user.id, file)
    return ResumeUploadResponse(resume_id=resume["id"], status="uploaded")


@router.get("/resumes", response_model=list[ResumeRead])
def list_resumes(db: DbSession, current_user: CurrentUser) -> list[ResumeRead]:
    return [ResumeRead(**item) for item in JobPortalService(db).list_resumes(current_user.id)]


@router.get("/resumes/variants", response_model=list[ResumeVariantListRead])
def list_resume_variants(
    db: DbSession, current_user: CurrentUser
) -> list[ResumeVariantListRead]:
    return [
        ResumeVariantListRead(**item)
        for item in JobPortalService(db).list_resume_variants(current_user.id)
    ]


@router.get("/resumes/tailored", response_model=list[TailoredResumeListItem])
def list_tailored_resumes(db: DbSession, current_user: CurrentUser) -> list[TailoredResumeListItem]:
    return [
        TailoredResumeListItem(**item)
        for item in JobPortalService(db).list_tailored_resume_tasks(current_user.id)
    ]


@router.get("/resumes/tailored/{task_id}", response_model=ResumeTailoringTaskRead)
def get_tailored_task(db: DbSession, current_user: CurrentUser, task_id: UUID) -> ResumeTailoringTaskRead:
    return ResumeTailoringTaskRead(**JobPortalService(db).get_resume_tailoring_task(current_user.id, task_id))


@router.post("/resumes/tailored/{task_id}/retry", response_model=ResumeTailoringTaskRead)
def retry_tailored_task(db: DbSession, current_user: CurrentUser, task_id: UUID) -> ResumeTailoringTaskRead:
    return ResumeTailoringTaskRead(**JobPortalService(db).retry_resume_tailoring_task(current_user.id, task_id))


@router.get("/resumes/{resume_id}/parsed", response_model=ResumeRead)
def get_resume(db: DbSession, current_user: CurrentUser, resume_id: UUID) -> ResumeRead:
    return ResumeRead(**JobPortalService(db).get_resume(current_user.id, resume_id))


@router.get("/resumes/{resume_id}/graph", response_model=ResumeGraphRead)
def get_resume_graph(db: DbSession, current_user: CurrentUser, resume_id: UUID) -> ResumeGraphRead:
    return ResumeGraphRead(**JobPortalService(db).get_resume_graph(current_user.id, resume_id))


@router.post("/resumes/{resume_id}/parse", response_model=ResumeParseTaskRead, status_code=status.HTTP_202_ACCEPTED)
def parse_resume(
    db: DbSession, current_user: CurrentUser, resume_id: UUID
) -> ResumeParseTaskRead:
    return ResumeParseTaskRead(
        **JobPortalService(db).enqueue_resume_parse(current_user.id, resume_id)
    )


@router.get("/resumes/{resume_id}/parse-status", response_model=ResumeParseStatusRead)
def resume_parse_status(
    db: DbSession, current_user: CurrentUser, resume_id: UUID
) -> ResumeParseStatusRead:
    return ResumeParseStatusRead(
        **JobPortalService(db).get_resume_parse_status(current_user.id, resume_id)
    )


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
        current_user.id,
        page=page,
        limit=limit,
        location=location,
        skills=skills,
        company=company,
    )


@router.get("/opportunities", response_model=OpportunityMapRead)
def list_opportunities(db: DbSession, current_user: CurrentUser) -> OpportunityMapRead:
    return OpportunityMapRead(**JobPortalService(db).list_opportunity_map(current_user.id))


@router.get("/jobs/{job_id}", response_model=JobDetailRead)
def get_job(db: DbSession, current_user: CurrentUser, job_id: UUID) -> JobDetailRead:
    return JobDetailRead(**JobPortalService(db).get_job(current_user.id, job_id))


@router.post("/jobs/{job_id}/rewrite", response_model=ResumeTailoringTaskCreateRead, status_code=status.HTTP_202_ACCEPTED)
def rewrite_job(db: DbSession, current_user: CurrentUser, job_id: UUID) -> ResumeTailoringTaskCreateRead:
    return ResumeTailoringTaskCreateRead(**JobPortalService(db).create_resume_tailoring_task(current_user.id, job_id))


@router.post("/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def create_feedback(
    db: DbSession, current_user: CurrentUser, payload: FeedbackCreateRequest
) -> FeedbackRead:
    return FeedbackRead(**JobPortalService(db).create_feedback(current_user.id, payload))


@router.post("/applications", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_application(
    db: DbSession, current_user: CurrentUser, payload: ApplicationCreateRequest
) -> dict:
    return JobPortalService(db).create_application(current_user.id, payload.job_id)


@router.get("/applications", response_model=list[ApplicationRead])
def list_applications(db: DbSession, current_user: CurrentUser) -> list[ApplicationRead]:
    return [
        ApplicationRead(**item)
        for item in JobPortalService(db).list_applications(current_user.id)
    ]


@router.patch("/applications/{application_id}", response_model=ApplicationRead)
def update_application(
    db: DbSession,
    current_user: CurrentUser,
    application_id: UUID,
    payload: ApplicationStatusUpdateRequest,
) -> ApplicationRead:
    return ApplicationRead(
        **JobPortalService(db).update_application_status(
            current_user.id, application_id, payload.status
        )
    )


@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(db: DbSession, current_user: CurrentUser, application_id: UUID) -> None:
    JobPortalService(db).delete_application(current_user.id, application_id)


@router.get("/notifications", response_model=NotificationSummary)
def list_notifications(db: DbSession, current_user: CurrentUser) -> NotificationSummary:
    payload = JobPortalService(db).list_notifications(current_user.id)
    return NotificationSummary(
        unread_count=payload["unread_count"],
        items=[NotificationRead(**item) for item in payload["items"]],
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    db: DbSession, current_user: CurrentUser, notification_id: UUID
) -> NotificationRead:
    return NotificationRead(
        **JobPortalService(db).mark_notification_read(current_user.id, notification_id)
    )


@router.post("/admin/ingest/run", status_code=status.HTTP_202_ACCEPTED)
def run_ingest(db: DbSession, _: AdminUser) -> dict:
    return JobPortalService(db).ingest_jobs()


@router.post("/admin/job-imports/preview", response_model=JobImportPreviewResponse)
def preview_job_import(
    db: DbSession, current_user: AdminUser, file: ResumeUploadFile
) -> JobImportPreviewResponse:
    return JobImportPreviewResponse(**JobImportService(db).preview_upload(current_user.id, file))


@router.post("/admin/job-imports/confirm", response_model=JobImportConfirmResponse)
def confirm_job_import(
    db: DbSession, current_user: AdminUser, payload: JobImportConfirmRequest
) -> JobImportConfirmResponse:
    return JobImportConfirmResponse(
        **JobImportService(db).confirm_import(current_user.id, payload.batch_id)
    )


@router.get("/admin/job-imports", response_model=JobImportHistoryResponse)
def list_job_imports(db: DbSession, current_user: AdminUser) -> JobImportHistoryResponse:
    return JobImportHistoryResponse(
        **JobImportService(db).list_history(current_user.id)
    )

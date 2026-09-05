from __future__ import annotations

import io
import logging
import math
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.llm.client import LLMConfigurationError, LLMRequestError, LLMResponseFormatError
from app.llm.structured_client import generate_structured_json
from app.models.application import Application
from app.models.job import Job
from app.models.notification import Notification
from app.models.resume import Resume
from app.models.resume_rewrite import ResumeRewrite
from app.schemas.ai import ResumeAnalysisResult, ResumeRewriteResult
from app.schemas.portal import JobListSummary, PaginatedJobReadResponse
from app.services.embedding_service import embed_text

logger = logging.getLogger(__name__)

STATE_TRANSITIONS: dict[str, set[str]] = {
    "applied": {"shortlisted", "interview", "completed", "withdrawn"},
    "shortlisted": {"interview", "completed", "withdrawn"},
    "interview": {"completed", "withdrawn"},
    "completed": set(),
    "withdrawn": set(),
}
SKILL_KEYWORDS = {
    "python",
    "fastapi",
    "sqlalchemy",
    "postgresql",
    "react",
    "nextjs",
    "javascript",
    "typescript",
    "docker",
    "aws",
    "linux",
    "rest",
    "graphql",
    "html",
    "css",
    "tailwind",
    "git",
    "testing",
}
SAMPLE_JOBS = [
    {
        "source": "arbeitnow",
        "external_id": "sample-001",
        "job_title": "Backend Engineer",
        "company_name": "Northwind Labs",
        "location": "Remote",
        "city_location": None,
        "country_location": None,
        "pay_period": None,
        "mid_salary_sgd": None,
        "source_id": None,
        "external_apply_url": "https://example.com/jobs/backend-engineer",
        "job_description": "Build FastAPI services, PostgreSQL data models, and job matching workflows.",
    },
    {
        "source": "arbeitnow",
        "external_id": "sample-002",
        "job_title": "Frontend Engineer",
        "company_name": "Contoso",
        "location": "Singapore",
        "city_location": None,
        "country_location": None,
        "pay_period": None,
        "mid_salary_sgd": None,
        "source_id": None,
        "external_apply_url": "https://example.com/jobs/frontend-engineer",
        "job_description": "Build React and Next.js interfaces with careful state management and forms.",
    },
]


class JobPortalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def dashboard_summary(self, user_id: UUID) -> dict[str, object]:
        resumes_total = self.db.scalar(select(func.count()).select_from(Resume).where(Resume.user_id == user_id)) or 0
        jobs_total = self.db.scalar(select(func.count()).select_from(Job).where(Job.is_active.is_(True))) or 0
        applications_total = self.db.scalar(
            select(func.count()).select_from(Application).where(Application.user_id == user_id)
        ) or 0
        unread_notifications = self.db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        ) or 0
        active_resume_exists = (
            self.db.scalar(
                select(Resume.id).where(Resume.user_id == user_id, Resume.is_active.is_(True))
            )
            is not None
        )
        jobs_matched = self._matching_jobs_count(user_id)
        return {
            "resumes_total": resumes_total,
            "active_resume_exists": active_resume_exists,
            "jobs_total": jobs_total,
            "jobs_matched": jobs_matched,
            "applications_total": applications_total,
            "unread_notifications": unread_notifications,
        }

    def list_resumes(self, user_id: UUID) -> list[dict[str, object]]:
        resumes = list(
            self.db.scalars(select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc()))
        )
        return [self._serialize_resume(resume) for resume in resumes]

    def upload_resume(self, user_id: UUID, upload: UploadFile) -> dict[str, object]:
        data = upload.file.read()
        if len(data) > settings.max_resume_upload_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is too large.")
        file_name = upload.filename or "resume"
        file_path = self._save_upload(user_id, file_name, data)
        parsed_text = self._extract_text(file_name, data)
        cleaned_text = self._strip_pii(parsed_text)
        analysis = self._analyze_resume_with_groq(cleaned_text)
        embedding = embed_text(cleaned_text)
        self.db.query(Resume).filter(Resume.user_id == user_id, Resume.is_active.is_(True)).update(
            {Resume.is_active: False}, synchronize_session=False
        )
        resume = Resume(
            user_id=user_id,
            file_name=file_name,
            file_url=file_path,
            parsed_text=cleaned_text,
            extracted_skills=analysis.skills,
            embedding=embedding,
            is_active=True,
        )
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)
        return self._serialize_resume(resume)

    def get_resume(self, user_id: UUID, resume_id: UUID) -> dict[str, object]:
        resume = self._get_resume(resume_id, user_id)
        return self._serialize_resume(resume)

    def delete_resume(self, user_id: UUID, resume_id: UUID) -> None:
        resume = self._get_resume(resume_id, user_id)
        file_path = Path(resume.file_url)
        self.db.delete(resume)
        self.db.commit()
        if file_path.exists():
            file_path.unlink()

    def list_jobs(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        limit: int = 20,
        location: str | None = None,
        skills: str | None = None,
        company: str | None = None,
    ) -> PaginatedJobReadResponse:
        resume = self._get_active_resume(user_id)
        filters = [Job.is_active.is_(True)]
        if location:
            filters.append(Job.location.ilike(f"%{location}%"))
        if company:
            filters.append(Job.company_name.ilike(f"%{company}%"))
        skill_terms = [term.strip().lower() for term in skills.split(",")] if skills else []
        if skill_terms:
            filters.append(
                or_(*(func.lower(Job.job_description).contains(term) for term in skill_terms))
            )

        query = select(Job).where(*filters)
        count = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        salary_query = select(Job.mid_salary_sgd, Job.pay_period).where(*filters)
        salary_values = [
            self._monthly_salary(mid_salary, pay_period)
            for mid_salary, pay_period in self.db.execute(salary_query)
        ]
        salary_values = [value for value in salary_values if value is not None]
        jobs = list(
            self.db.scalars(
                query.order_by(func.random())
                .offset(max(page - 1, 0) * limit)
                .limit(limit)
            )
        )
        items = [
            {
                **self._serialize_job(job),
                "match_score": round(self._match_score(resume.embedding, job.embedding), 4)
                if resume and resume.embedding
                else 0.0,
            }
            for job in jobs
        ]
        return PaginatedJobReadResponse(
            items=items,
            pagination={
                "page": page,
                "page_size": limit,
                "total": count,
                "total_pages": math.ceil(count / limit) if limit else 0,
            },
            summary=JobListSummary(
                jobs_total=count,
                salary_range={
                    "min": round(min(salary_values), 2) if salary_values else None,
                    "max": round(max(salary_values), 2) if salary_values else None,
                },
            ),
        )

    def get_job(self, user_id: UUID, job_id: UUID) -> dict[str, object]:
        job = self._get_job(job_id)
        resume = self._get_active_resume(user_id)
        score = self._match_score(resume.embedding if resume and resume.embedding else None, job.embedding)
        return {**self._serialize_job(job), "match_score": round(score, 4)}

    def rewrite_job_resume(self, user_id: UUID, job_id: UUID) -> dict[str, object]:
        existing = self.db.scalar(
            select(ResumeRewrite).where(ResumeRewrite.user_id == user_id, ResumeRewrite.job_id == job_id)
        )
        if existing:
            return {"rewritten_text": existing.rewritten_text, "cached": True}
        daily_count = self.db.scalar(
            select(func.count())
            .select_from(ResumeRewrite)
            .where(
                ResumeRewrite.user_id == user_id,
                ResumeRewrite.created_at >= datetime.now(UTC) - timedelta(days=1),
            )
        ) or 0
        if daily_count >= settings.daily_rewrite_limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="You have reached today's rewrite limit.")
        resume = self._get_active_resume(user_id)
        if resume is None or not resume.parsed_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload and parse a resume first.")
        job = self._get_job(job_id)
        rewritten = self._rewrite_resume_with_groq(resume.parsed_text, job.job_description)
        record = ResumeRewrite(user_id=user_id, job_id=job_id, rewritten_text=rewritten)
        self.db.add(record)
        self.db.commit()
        return {"rewritten_text": rewritten, "cached": False}

    def create_application(self, user_id: UUID, job_id: UUID) -> dict[str, object]:
        existing = self.db.scalar(
            select(Application).where(Application.user_id == user_id, Application.job_id == job_id)
        )
        job = self._get_job(job_id)
        resume = self._get_active_resume(user_id)
        score = self._match_score(resume.embedding if resume and resume.embedding else None, job.embedding)
        if existing:
            return {"application": self._serialize_application(existing, job), "apply_url": job.external_apply_url, "created": False}
        application = Application(
            user_id=user_id,
            job_id=job.id,
            job_name_snapshot=job.job_title,
            company_name_snapshot=job.company_name,
            location_snapshot=job.location,
            external_apply_url_snapshot=job.external_apply_url,
            status="applied",
            match_score=round(score, 4),
        )
        self.db.add(application)
        self.db.add(
            Notification(
                user_id=user_id,
                message=f"Application recorded: {job.job_title} @ {job.company_name or 'Unknown'}",
            )
        )
        self.db.commit()
        self.db.refresh(application)
        return {
            "application": self._serialize_application(application, job),
            "apply_url": job.external_apply_url,
            "created": True,
        }

    def list_applications(self, user_id: UUID) -> list[dict[str, object]]:
        applications = list(
            self.db.scalars(
                select(Application).where(Application.user_id == user_id).order_by(Application.applied_at.desc())
            )
        )
        jobs_by_id = {job.id: job for job in self.db.scalars(select(Job).where(Job.id.in_([app.job_id for app in applications if app.job_id])))}
        return [self._serialize_application(app, jobs_by_id.get(app.job_id)) for app in applications]

    def update_application_status(self, user_id: UUID, application_id: UUID, status_value: str) -> dict[str, object]:
        application = self.db.scalar(
            select(Application).where(Application.id == application_id, Application.user_id == user_id)
        )
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
        if status_value not in STATE_TRANSITIONS.get(application.status, set()) and status_value != application.status:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="This status transition is not allowed.")
        application.status = status_value
        self.db.add(application)
        self.db.add(Notification(user_id=user_id, message=f"Application status updated to {status_value}."))
        self.db.commit()
        job = self.db.get(Job, application.job_id) if application.job_id else None
        return self._serialize_application(application, job)

    def list_notifications(self, user_id: UUID) -> dict[str, object]:
        items = list(
            self.db.scalars(
                select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
            )
        )
        unread_count = sum(1 for item in items if item.read_at is None)
        return {
            "unread_count": unread_count,
            "items": [self._serialize_notification(item) for item in items],
        }

    def mark_notification_read(self, user_id: UUID, notification_id: UUID) -> dict[str, object]:
        notification = self.db.scalar(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
        )
        if notification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
        notification.read_at = datetime.now(UTC)
        self.db.add(notification)
        self.db.commit()
        return self._serialize_notification(notification)

    def ingest_jobs(self) -> dict[str, int]:
        inserted = 0
        for payload in self._fetch_jobs():
            exists = self.db.scalar(
                select(Job.id).where(
                    Job.source == payload["source"], Job.external_id == payload["external_id"]
                )
            )
            if exists is not None:
                continue
            job = Job(
                job_title=payload["job_title"],
                    job_description=payload["job_description"],
                    source_id=payload.get("source_id"),
                    company_name=payload.get("company_name"),
                    location=payload.get("location"),
                    city_location=payload.get("city_location"),
                    country_location=payload.get("country_location"),
                    pay_period=payload.get("pay_period"),
                    mid_salary_sgd=payload.get("mid_salary_sgd"),
                    source=payload["source"],
                    external_id=payload["external_id"],
                    external_apply_url=payload["external_apply_url"],
                embedding=embed_text(payload["job_description"]),
                skill_tags=self._extract_skills(payload["job_description"]),
            )
            self.db.add(job)
            inserted += 1
        self.db.commit()
        return {"inserted": inserted}

    def _fetch_jobs(self) -> list[dict[str, object]]:
        jobs = list(SAMPLE_JOBS)
        try:
            response = httpx.get(settings.arbeitnow_api_url, timeout=10)
            if response.status_code == 200:
                payload = response.json()
                for item in payload.get("data", [])[:10]:
                    jobs.append(
                        {
                            "source": "arbeitnow",
                            "external_id": str(item.get("slug") or item.get("id") or uuid4()),
                            "job_title": item.get("title") or "Untitled",
                            "company_name": item.get("company_name"),
                            "location": item.get("location"),
                            "city_location": None,
                            "country_location": None,
                            "pay_period": None,
                            "mid_salary_sgd": None,
                            "source_id": None,
                            "external_apply_url": item.get("url") or item.get("apply_url") or "",
                            "job_description": item.get("description") or "",
                        }
                    )
        except Exception:
            logger.warning("job ingestion fallback to samples", exc_info=True)
        return [job for job in jobs if job["external_apply_url"]]

    def _save_upload(self, user_id: UUID, file_name: str, data: bytes) -> str:
        folder = Path(settings.upload_dir) / "resumes" / str(user_id)
        folder.mkdir(parents=True, exist_ok=True)
        suffix = Path(file_name).suffix or ".txt"
        file_path = folder / f"{uuid4()}{suffix}"
        file_path.write_bytes(data)
        return str(file_path)

    def _extract_text(self, file_name: str, data: bytes) -> str:
        lower = file_name.lower()
        if lower.endswith(".docx"):
            try:
                from docx import Document

                doc = Document(io.BytesIO(data))
                return "\n".join(paragraph.text for paragraph in doc.paragraphs)
            except Exception:
                pass
        if lower.endswith(".pdf"):
            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(data))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception:
                pass
        return data.decode("utf-8", errors="ignore")

    def _strip_pii(self, text: str) -> str:
        text = re.sub(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[redacted-email]", text)
        text = re.sub(r"\+?\d[\d\s().-]{7,}\d", "[redacted-phone]", text)
        return text

    def _extract_skills(self, text: str) -> list[str]:
        lowered = text.lower()
        return [skill for skill in sorted(SKILL_KEYWORDS) if skill in lowered]

    def _match_score(self, resume_embedding: list[float] | None, job_embedding: list[float] | None) -> float:
        if not resume_embedding or not job_embedding:
            return 0.0
        size = min(len(resume_embedding), len(job_embedding))
        dot = sum(resume_embedding[i] * job_embedding[i] for i in range(size))
        resume_norm = math.sqrt(sum(v * v for v in resume_embedding[:size])) or 1.0
        job_norm = math.sqrt(sum(v * v for v in job_embedding[:size])) or 1.0
        return max(0.0, min(1.0, dot / (resume_norm * job_norm)))

    def _annualized_salary(self, mid_salary: float | None, pay_period: str | None) -> float | None:
        if mid_salary is None:
            return None
        if pay_period and pay_period.lower().startswith("month"):
            return mid_salary * 12
        return mid_salary

    def _monthly_salary(self, mid_salary: float | None, pay_period: str | None) -> float | None:
        if mid_salary is None:
            return None
        if pay_period and pay_period.lower().startswith("annual"):
            return mid_salary / 12
        return mid_salary

    def _get_job(self, job_id: UUID) -> Job:
        job = self.db.get(Job, job_id)
        if job is None or not job.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
        return job

    def _get_resume(self, resume_id: UUID, user_id: UUID) -> Resume:
        resume = self.db.get(Resume, resume_id)
        if resume is None or resume.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
        return resume

    def _get_active_resume(self, user_id: UUID) -> Resume | None:
        return self.db.scalar(
            select(Resume)
            .where(Resume.user_id == user_id, Resume.is_active.is_(True))
            .order_by(Resume.created_at.desc())
        )

    def _build_job_search_query(
        self,
        resume_embedding: list[float],
        *,
        location: str | None,
        skills: str | None,
        company: str | None,
    ):
        cosine_distance = Job.embedding.cosine_distance(resume_embedding).label("distance")
        match_score = (1 - cosine_distance).label("match_score")
        query = (
            select(Job, match_score.label("match_score"))
            .where(Job.is_active.is_(True), Job.embedding.is_not(None))
            .where(cosine_distance <= 1 - settings.match_score_threshold)
        )
        if location:
            query = query.where(Job.location.ilike(f"%{location}%"))
        if company:
            query = query.where(Job.company_name.ilike(f"%{company}%"))
        skill_terms = [term.strip().lower() for term in skills.split(",")] if skills else []
        if skill_terms:
            query = query.where(
                or_(
                    *(
                        func.lower(Job.job_description).contains(term)
                        for term in skill_terms
                    )
                )
            )
        return query.order_by(cosine_distance.asc(), Job.ingested_at.desc())

    def _matching_jobs_count(self, user_id: UUID) -> int:
        resume = self._get_active_resume(user_id)
        if resume is None or resume.embedding is None:
            return 0
        query = self._build_job_search_query(resume.embedding, location=None, skills=None, company=None)
        return self.db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0

    def _analyze_resume_with_groq(self, cleaned_text: str) -> ResumeAnalysisResult:
        prompt = (
            "Extract a concise skills list, a short summary, and a few experience highlights from the resume. "
            "Return only the fields requested. Do not invent skills. Use the resume text only.\n\n"
            f"Resume text:\n{cleaned_text}"
        )
        try:
            payload = generate_structured_json(
                "You extract structured resume information for a job portal.",
                prompt,
                response_model=ResumeAnalysisResult,
            )
        except (LLMConfigurationError, LLMRequestError, LLMResponseFormatError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The resume parsing service is temporarily unavailable. Please try again later.",
            ) from exc
        return ResumeAnalysisResult.model_validate(payload)

    def _rewrite_resume_with_groq(self, resume_text: str, job_description: str) -> str:
        prompt = (
            "Rewrite the resume to better fit the target role. "
            "Only rephrase, reorder, and emphasize content already present in the source resume. "
            "Do not add new skills, credentials, or work history. Return one polished resume body.\n\n"
            f"Source resume:\n{resume_text}\n\nTarget job description:\n{job_description}"
        )
        try:
            payload = generate_structured_json(
                "You tailor resumes without fabricating experience.",
                prompt,
                response_model=ResumeRewriteResult,
            )
        except (LLMConfigurationError, LLMRequestError, LLMResponseFormatError) as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The resume rewriting service is temporarily unavailable. Please try again later.",
            ) from exc
        return ResumeRewriteResult.model_validate(payload).rewritten_text

    def _serialize_job(self, job: Job) -> dict[str, object]:
        return {
            "id": job.id,
            "job_title": job.job_title,
            "job_description": job.job_description,
            "source_id": job.source_id,
            "company_name": job.company_name,
            "location": job.location,
            "city_location": job.city_location,
            "country_location": job.country_location,
            "pay_period": job.pay_period,
            "mid_salary_sgd": job.mid_salary_sgd,
            "source": job.source,
            "external_id": job.external_id,
            "external_apply_url": job.external_apply_url,
            "skill_tags": job.skill_tags or [],
            "is_active": job.is_active,
            "ingested_at": job.ingested_at,
        }

    def _serialize_resume(self, resume: Resume) -> dict[str, object]:
        return {
            "id": resume.id,
            "user_id": resume.user_id,
            "file_name": resume.file_name,
            "file_url": resume.file_url,
            "parsed_text": resume.parsed_text,
            "extracted_skills": resume.extracted_skills or [],
            "embedding_ready": bool(resume.embedding),
            "is_active": resume.is_active,
            "created_at": resume.created_at,
            "updated_at": resume.updated_at,
        }

    def _serialize_application(self, application: Application, job: Job | None) -> dict[str, object]:
        data = {
            "id": application.id,
            "user_id": application.user_id,
            "job_id": application.job_id,
            "job_name_snapshot": application.job_name_snapshot,
            "company_name_snapshot": application.company_name_snapshot,
            "location_snapshot": application.location_snapshot,
            "external_apply_url_snapshot": application.external_apply_url_snapshot,
            "status": application.status,
            "match_score": application.match_score,
            "applied_at": application.applied_at,
            "updated_at": application.updated_at,
        }
        if job is not None:
            data["job"] = self._serialize_job(job)
        return data

    def _serialize_notification(self, notification: Notification) -> dict[str, object]:
        return {
            "id": notification.id,
            "user_id": notification.user_id,
            "message": notification.message,
            "read_at": notification.read_at,
            "created_at": notification.created_at,
        }

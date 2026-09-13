from __future__ import annotations

import io
import logging
import math
import re
from collections import defaultdict
from dataclasses import dataclass
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
from app.models.applicant_profile import ApplicantProfile
from app.models.application import Application
from app.models.career_intelligence import (
    CandidateGraph,
    CandidateJobMatch,
    FeedbackEvent,
    JobMarketProfile,
    ResumeTailoringTask,
    ResumeVariant,
)
from app.models.job import Job
from app.models.notification import Notification
from app.models.resume import Resume
from app.models.resume_parse_task import ResumeParseTask
from app.models.resume_rewrite import ResumeRewrite
from app.models.user import User
from app.schemas.ai import OpportunityScoreVector, ResumeAnalysisResult, ResumeRewriteResult, TailoredResumeResult
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

SECTION_KEYWORDS = {
    "education": {"education", "academic background", "education and training"},
    "experience": {"experience", "work experience", "internship", "employment", "professional experience"},
    "projects": {"projects", "project experience", "selected projects"},
    "achievements": {"achievements", "awards", "honors", "honours", "recognition"},
    "publications": {"publications", "publication", "papers", "journal", "conference"},
    "skills": {"skills", "technical skills", "core skills", "competencies"},
}

BLOCKED_PII_PATTERNS = (
    re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
)

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


@dataclass(slots=True)
class _OpportunityParts:
    score: float
    category: str
    vector: OpportunityScoreVector
    breakdown: dict[str, float]
    rationale: list[str]
    transition_difficulty: str
    data_confidence: float


@dataclass(slots=True)
class _ResumeTextProfile:
    source: str
    raw_text: str
    cleaned_text: str
    line_count: int
    title_count: int
    section_hits: dict[str, int]
    char_count: int
    cleaned_char_count: int
    pypdf_score: float
    fallback_score: float | None = None


class JobPortalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._last_resume_analysis_diagnostics: dict[str, object] = {}

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

    def get_candidate_profile(self, user_id: UUID) -> dict[str, object]:
        graph = self._get_candidate_graph(user_id, create_if_missing=False)
        user = self.db.get(User, user_id)
        profile = self.db.get(ApplicantProfile, user_id)
        profile_payload = {
            "first_name": profile.first_name if profile else (user.display_name if user and user.display_name else user.username if user else ""),
            "last_name": profile.last_name if profile else (user.username if user else ""),
            "years_experience": profile.years_experience if profile else 0,
            "current_company": profile.current_company if profile else None,
            "headline": profile.headline if profile else None,
            "employment_status": profile.employment_status if profile else "unemployed",
            "notice_period": profile.notice_period if profile else None,
        }
        return {
            "user_id": user_id,
            "profile": profile_payload,
            "preferences": graph.preferences if graph else {},
            "constraints": graph.constraints if graph else {},
            "confirmed": graph.user_confirmed if graph else False,
        }

    def update_candidate_profile(self, user_id: UUID, payload) -> dict[str, object]:
        graph = self._get_candidate_graph(user_id, create_if_missing=True)
        profile = self.db.get(ApplicantProfile, user_id)
        if profile is not None:
            for key, value in payload.profile.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            self.db.add(profile)
        if graph is not None:
            graph.preferences = payload.preferences
            graph.constraints = payload.constraints
            graph.user_confirmed = payload.confirmed
            if payload.profile:
                graph.source_spans = [*(graph.source_spans or []), {"type": "profile_override", **payload.profile}]
            self.db.add(graph)
        self.db.commit()
        return self.get_candidate_profile(user_id)

    def list_resumes(self, user_id: UUID) -> list[dict[str, object]]:
        resumes = list(
            self.db.scalars(select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc()))
        )
        return [self._serialize_resume(resume) for resume in resumes]

    def list_resume_variants(self, user_id: UUID) -> list[dict[str, object]]:
        variants = list(
            self.db.scalars(
                select(ResumeVariant)
                .where(ResumeVariant.user_id == user_id)
                .order_by(ResumeVariant.created_at.desc())
            )
        )
        latest_by_job: dict[UUID, ResumeVariant] = {}
        for variant in variants:
            latest_by_job.setdefault(variant.job_id, variant)
        return [self._serialize_resume_variant(variant, include_source_file=True) for variant in latest_by_job.values()]

    def list_tailored_resume_tasks(self, user_id: UUID) -> list[dict[str, object]]:
        """Return one current workspace item per job, including unfinished tasks."""
        tasks = list(
            self.db.scalars(
                select(ResumeTailoringTask)
                .where(ResumeTailoringTask.user_id == user_id)
                .order_by(ResumeTailoringTask.created_at.desc())
            )
        )
        latest_by_job: dict[UUID, ResumeTailoringTask] = {}
        for task in tasks:
            latest_by_job.setdefault(task.job_id, task)
        result = [self._serialize_resume_tailoring_task(task) for task in latest_by_job.values()]

        # Keep variants created by the previous synchronous flow visible until they are
        # replaced by a task-backed result.
        for variant_payload in self.list_resume_variants(user_id):
            if variant_payload["job_id"] in latest_by_job:
                continue
            result.append(
                {
                    "id": variant_payload["id"],
                    "user_id": variant_payload["user_id"],
                    "resume_id": variant_payload["resume_id"],
                    "job_id": variant_payload["job_id"],
                    "job_title": variant_payload["job_title"],
                    "company_name": variant_payload["company_name"],
                    "source_file_name": variant_payload.get("source_file_name"),
                    "status": "completed",
                    "stage": "completed",
                    "progress": 100,
                    "error_message": None,
                    "attempts": 0,
                    "created_at": variant_payload["created_at"],
                    "updated_at": variant_payload["created_at"],
                    "finished_at": variant_payload["created_at"],
                    "variant": variant_payload,
                }
            )
        return sorted(result, key=lambda item: item["created_at"], reverse=True)

    def create_resume_tailoring_task(self, user_id: UUID, job_id: UUID) -> dict[str, object]:
        resume = self._get_active_resume(user_id)
        if resume is None or not resume.parsed_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload and parse a resume first.")
        self._get_job(job_id)
        existing = self.db.scalar(
            select(ResumeTailoringTask).where(
                ResumeTailoringTask.user_id == user_id,
                ResumeTailoringTask.job_id == job_id,
                ResumeTailoringTask.status.in_(("queued", "running")),
            ).order_by(ResumeTailoringTask.created_at.desc())
        )
        if existing is not None:
            return self._serialize_resume_tailoring_task(existing)
        task = ResumeTailoringTask(user_id=user_id, resume_id=resume.id, job_id=job_id)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return self._serialize_resume_tailoring_task(task)

    def get_resume_tailoring_task(self, user_id: UUID, task_id: UUID) -> dict[str, object]:
        task = self.db.scalar(select(ResumeTailoringTask).where(ResumeTailoringTask.id == task_id, ResumeTailoringTask.user_id == user_id))
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailored resume task not found.")
        return self._serialize_resume_tailoring_task(task)

    def retry_resume_tailoring_task(self, user_id: UUID, task_id: UUID) -> dict[str, object]:
        task = self.db.scalar(select(ResumeTailoringTask).where(ResumeTailoringTask.id == task_id, ResumeTailoringTask.user_id == user_id))
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tailored resume task not found.")
        if task.status != "failed":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed tasks can be retried.")
        task.status, task.stage, task.progress, task.error_message = "queued", "queued", 0, None
        task.finished_at = None
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return self._serialize_resume_tailoring_task(task)

    def upload_resume(self, user_id: UUID, upload: UploadFile) -> dict[str, object]:
        data = upload.file.read()
        if len(data) > settings.max_resume_upload_bytes:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is too large.")
        file_name = upload.filename or "resume"
        file_path = self._save_upload(user_id, file_name, data)
        self.db.query(Resume).filter(Resume.user_id == user_id, Resume.is_active.is_(True)).update(
            {Resume.is_active: False}, synchronize_session=False
        )
        resume = Resume(
            user_id=user_id,
            file_name=file_name,
            file_url=file_path,
            is_active=True,
        )
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)
        return self._serialize_resume(resume)

    def enqueue_resume_parse(self, user_id: UUID, resume_id: UUID) -> dict[str, object]:
        resume = self._get_resume(resume_id, user_id)
        existing = self.db.scalar(
            select(ResumeParseTask)
            .where(
                ResumeParseTask.resume_id == resume.id,
                ResumeParseTask.status.in_(("queued", "running")),
            )
            .order_by(ResumeParseTask.created_at.desc())
        )
        if existing is not None:
            return self._serialize_resume_parse_task(existing)

        latest = self.db.scalar(
            select(ResumeParseTask)
            .where(ResumeParseTask.resume_id == resume.id)
            .order_by(ResumeParseTask.created_at.desc())
        )
        if latest is not None and latest.status == "completed":
            return self._serialize_resume_parse_task(latest)

        task = ResumeParseTask(resume_id=resume.id, user_id=user_id)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return self._serialize_resume_parse_task(task)

    def get_resume_parse_status(self, user_id: UUID, resume_id: UUID) -> dict[str, object]:
        self._get_resume(resume_id, user_id)
        task = self.db.scalar(
            select(ResumeParseTask)
            .where(
                ResumeParseTask.resume_id == resume_id,
                ResumeParseTask.user_id == user_id,
            )
            .order_by(ResumeParseTask.created_at.desc())
        )
        if task is None:
            return {
                "resume_id": resume_id,
                "task": None,
            }
        return {
            "resume_id": resume_id,
            "task": self._serialize_resume_parse_task(task),
        }

    def process_resume_parse_task(self, task_id: UUID, worker_id: str) -> None:
        task = self.db.get(ResumeParseTask, task_id)
        if task is None:
            return
        resume = self.db.get(Resume, task.resume_id)
        if resume is None:
            task.status = "failed"
            task.stage = "failed"
            task.error_message = "Resume file no longer exists."
            task.finished_at = datetime.now(UTC)
            self.db.commit()
            return

        try:
            data = Path(resume.file_url).read_bytes()
            self._update_resume_parse_task(task, "extracting", 20, worker_id)
            text_profile = self._extract_resume_text_profile(resume.file_name, data)
            cleaned_text = text_profile.cleaned_text
            self._update_resume_parse_task(task, "analyzing", 55, worker_id)
            analysis = self._analyze_resume_with_groq(text_profile)
            self._update_resume_parse_task(task, "embedding", 75, worker_id)
            embedding = embed_text(cleaned_text)
            self._update_resume_parse_task(task, "building_graph", 90, worker_id)
            resume.parsed_text = cleaned_text
            resume.extracted_skills = analysis.skills
            resume.embedding = embedding
            self.db.add(resume)
            graph = self._upsert_candidate_graph(task.user_id, resume.id, analysis, cleaned_text)
            task.status = "completed"
            task.stage = "completed"
            task.progress = 100
            task.error_message = None
            task.diagnostics = self._build_parse_diagnostics(text_profile, analysis, graph, task)
            task.finished_at = datetime.now(UTC)
            task.heartbeat_at = datetime.now(UTC)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            failed_task = self.db.get(ResumeParseTask, task_id)
            if failed_task is not None:
                failed_task.status = "failed"
                failed_task.stage = "failed"
                failed_task.error_message = str(exc)[:2000] or "Resume parsing failed."
                failed_task.diagnostics = {
                    "mode": "failed",
                    "reason": type(exc).__name__,
                }
                failed_task.finished_at = datetime.now(UTC)
                failed_task.heartbeat_at = datetime.now(UTC)
                self.db.commit()
            logger.exception("resume.parse.failed task_id=%s", task_id)
            raise

    def process_resume_tailoring_task(self, task_id: UUID, worker_id: str) -> None:
        task = self.db.get(ResumeTailoringTask, task_id)
        if task is None:
            return
        resume = self.db.get(Resume, task.resume_id)
        job = self.db.get(Job, task.job_id)
        if resume is None or job is None or not resume.parsed_text:
            task.status, task.stage, task.error_message = "failed", "failed", "Resume or job data is unavailable."
            task.finished_at = datetime.now(UTC)
            self.db.commit()
            return
        try:
            task.status, task.stage, task.progress, task.worker_id = "running", "preparing", 15, worker_id
            task.started_at = task.started_at or datetime.now(UTC)
            self.db.commit()
            requirements = self._get_job_requirement_summary(job)
            self._update_tailoring_task(task, "generating", 55, worker_id)
            result = self._generate_tailored_resume(resume.parsed_text, job.job_description, requirements)
            graph = self._get_candidate_graph(task.user_id, resume.id, create_if_missing=False)
            plan = self._build_resume_plan(resume, graph, job, requirements) if graph else {}
            claims = self._build_resume_claims(plan, graph, requirements, result.rewritten_text) if graph else []
            validation = result.validation_results or (
                self._validate_resume_claims(claims, graph, requirements) if graph else []
            )
            variant = self.db.scalar(
                select(ResumeVariant)
                .where(ResumeVariant.user_id == task.user_id, ResumeVariant.job_id == task.job_id)
                .order_by(ResumeVariant.created_at.desc())
            )
            if variant is None:
                variant = ResumeVariant(user_id=task.user_id, resume_id=resume.id, job_id=job.id, rewritten_text=result.rewritten_text)
            variant.resume_id = resume.id
            variant.plan, variant.claims, variant.validation_results = plan, claims, validation
            variant.rewritten_text = result.rewritten_text
            variant.resume_sections = result.resume
            variant.change_summary = result.change_summary
            variant.evidence_used = result.evidence_used or [
                {"source": "resume", "text": evidence}
                for change in result.change_summary
                for evidence in (change.get("source_evidence") or [])
            ]
            variant.target_requirements = result.target_requirements
            self.db.add(variant)
            task.status, task.stage, task.progress, task.error_message = "completed", "completed", 100, None
            task.finished_at = datetime.now(UTC)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            failed = self.db.get(ResumeTailoringTask, task_id)
            if failed:
                failed.status, failed.stage, failed.error_message = "failed", "failed", str(exc)[:2000] or "Tailored resume generation failed."
                failed.finished_at = datetime.now(UTC)
                self.db.commit()
            logger.exception("resume.tailoring.failed task_id=%s", task_id)

    def _update_tailoring_task(self, task: ResumeTailoringTask, stage: str, progress: int, worker_id: str) -> None:
        task.status, task.stage, task.progress, task.worker_id = "running", stage, progress, worker_id
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

    def _generate_tailored_resume(self, resume_text: str, job_description: str, requirement_summary: dict[str, object]) -> TailoredResumeResult:
        prompt = (
            "Create a truthful tailored resume as structured JSON using only facts from the source. "
            "Never invent credentials, employers, dates, metrics, skills, or experience.\n"
            "Return ONLY a JSON object with exactly these keys:\n"
            "{\n"
            '  "resume": {"summary": "", "skills": [""], "experience": [""], "projects": [""], "education": [""], "achievements": [""], "publications": [""]},\n'
            '  "rewritten_text": "the complete polished resume",\n'
            '  "change_summary": [{"section": "", "action": "", "reason": "", "source_evidence": ""}],\n'
            '  "evidence_used": [{"claim": "", "evidence": ""}],\n'
            '  "target_requirements": [{"requirement": "", "matched_evidence": "", "coverage": ""}],\n'
            '  "validation_results": [{"status": "", "rule": "", "claim": "", "evidence_count": 0}]\n'
            "}\n"
            "Do not include markdown, commentary, or hidden chain-of-thought.\n\n"
            f"Source resume:\n{resume_text}\n\nTarget job:\n{job_description}\n\n"
            f"Requirements:\n{self._format_requirement_context(requirement_summary)}"
        )
        last_error: Exception | None = None
        for _ in range(2):
            try:
                result = TailoredResumeResult.model_validate(generate_structured_json(
                    "You produce truthful, evidence-grounded tailored resumes.", prompt, response_model=TailoredResumeResult
                ))
                return self._enforce_fidelity(resume_text, result)
            except (LLMConfigurationError, LLMRequestError, LLMResponseFormatError, ValueError) as exc:
                last_error = exc
        raise RuntimeError("Structured tailored resume generation failed after two attempts.") from last_error

    def _skill_in_source(self, skill: str, source_lower: str) -> bool:
        """Return True when a skill has at least one significant token in the source.

        Conservative by design: a skill is treated as grounded when its full text, or any
        alphanumeric token of three or more characters, appears in the source resume. Only
        skills with zero textual overlap are flagged, so legitimate rephrasings such as
        ``"Python (pandas)"`` against a resume that mentions ``Python`` are kept.
        """
        normalized = (skill or "").strip().lower()
        if not normalized:
            return True
        if normalized in source_lower:
            return True
        tokens = [
            token
            for token in re.findall(r"[a-z0-9+#.]+", normalized)
            if len(token) >= 3 and not token.isdigit()
        ]
        if not tokens:
            return normalized in source_lower
        return any(token in source_lower for token in tokens)

    def _enforce_fidelity(self, source_text: str, result: TailoredResumeResult) -> TailoredResumeResult:
        """Remove skills not grounded in the source resume and record the check.

        The LLM self-reports ``validation_results``, which the three-variant test showed can
        still hallucinate a few technical terms under heavy skill-gap pressure. This adds a
        deterministic post-generation check against the actual source text and strips any
        listed skill that has no presence in the resume.
        """
        raw_skills = result.resume.get("skills") or []
        skills = [item.get("name", "") if isinstance(item, dict) else item for item in raw_skills]
        # Drop the LLM's self-reported skills-fabrication entry; we replace it below with a
        # deterministic check against the actual source text (the self-report proved unreliable).
        result.validation_results = [
            entry
            for entry in result.validation_results
            if not (isinstance(entry, dict) and "skill" in str(entry.get("rule", "")).lower())
        ]
        if not skills:
            return result
        source_lower = (source_text or "").lower()
        unverified = [skill for skill in skills if not self._skill_in_source(skill, source_lower)]
        if not unverified:
            result.validation_results.append(
                {
                    "status": "pass",
                    "rule": "no fabricated skills (deterministic check)",
                    "claim": "Every listed skill was found in the source resume.",
                    "evidence_count": len(skills),
                }
            )
            return result
        result.resume["skills"] = [skill for skill in skills if skill not in unverified]
        result.validation_results.append(
            {
                "status": "fail",
                "rule": "no fabricated skills (deterministic check)",
                "claim": "Removed skills not present in the source resume.",
                "evidence_count": len(unverified),
                "removed_skills": unverified,
            }
        )
        return result

    def _update_resume_parse_task(
        self,
        task: ResumeParseTask,
        stage: str,
        progress: int,
        worker_id: str,
    ) -> None:
        task.status = "running"
        task.stage = stage
        task.progress = progress
        task.worker_id = worker_id
        task.heartbeat_at = datetime.now(UTC)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

    def get_resume(self, user_id: UUID, resume_id: UUID) -> dict[str, object]:
        resume = self._get_resume(resume_id, user_id)
        graph = self._get_candidate_graph(user_id, resume.id)
        return self._serialize_resume(resume, graph)

    def get_resume_graph(self, user_id: UUID, resume_id: UUID) -> dict[str, object]:
        resume = self._get_resume(resume_id, user_id)
        graph = self._get_candidate_graph(user_id, resume.id)
        variant = self._get_resume_variant(user_id, resume.id)
        return {
            "candidate_graph": self._serialize_candidate_graph(graph) if graph is not None else None,
            "resume": self._serialize_resume(resume, graph),
            "resume_variant": self._serialize_resume_variant(variant),
        }

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
            filters.append(or_(*(func.lower(Job.job_description).contains(term) for term in skill_terms)))

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
        items = [self._serialize_job(job, user_id=user_id, resume=resume) for job in jobs]
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

    def list_opportunity_map(self, user_id: UUID) -> dict[str, object]:
        resume = self._get_active_resume(user_id)
        if resume is None:
            return {
                "overview": self.dashboard_summary(user_id),
                "sections": [],
                "score_vector": OpportunityScoreVector().model_dump(mode="json"),
            }
        jobs = list(
            self.db.scalars(select(Job).where(Job.is_active.is_(True)).order_by(Job.ingested_at.desc()).limit(24))
        )
        scored_jobs = sorted(
            ((job, self._score_job(user_id, job, resume)) for job in jobs),
            key=lambda item: item[1].score,
            reverse=True,
        )
        sections = [
            {
                "title": "Easy Wins",
                "jobs": [
                    self._serialize_job(job, user_id=user_id, resume=resume, match=match)
                    for job, match in scored_jobs
                    if match.category == "easy_win"
                ],
            },
            {
                "title": "High-Potential",
                "jobs": [
                    self._serialize_job(job, user_id=user_id, resume=resume, match=match)
                    for job, match in scored_jobs
                    if match.category == "high_potential"
                ],
            },
            {
                "title": "Stretch",
                "jobs": [
                    self._serialize_job(job, user_id=user_id, resume=resume, match=match)
                    for job, match in scored_jobs
                    if match.category == "stretch"
                ],
            },
        ]
        return {
            "overview": self.dashboard_summary(user_id),
            "sections": [section for section in sections if section["jobs"]],
            "score_vector": (
                scored_jobs[0][1].vector.model_dump(mode="json")
                if scored_jobs
                else OpportunityScoreVector().model_dump(mode="json")
            ),
        }

    def get_job(self, user_id: UUID, job_id: UUID) -> dict[str, object]:
        job = self._get_job(job_id)
        resume = self._get_active_resume(user_id)
        requirement_summary = self._get_job_requirement_summary(job)
        if resume is None:
            return {
                **self._serialize_job(job),
                "canonical_job_profile": requirement_summary,
                "requirement_summary": requirement_summary,
                "opportunity_explanation": None,
            }
        match = self._score_job(user_id, job, resume)
        data = self._serialize_job(job, user_id=user_id, resume=resume, match=match)
        data["canonical_job_profile"] = requirement_summary
        data["requirement_summary"] = requirement_summary
        data["opportunity_explanation"] = {
            "what_fits": match.rationale[:3],
            "what_transfers": self._compute_transfer_notes(job, resume, match),
            "what_is_missing": self._compute_gap_notes(job, resume, match),
            "salary_context": self._salary_context(job),
            "confidence": round(match.data_confidence, 3),
            "transition_cost": match.transition_difficulty,
        }
        return data

    def rewrite_job_resume(self, user_id: UUID, job_id: UUID) -> dict[str, object]:
        existing_variant = self.db.scalar(
            select(ResumeVariant)
            .where(
                ResumeVariant.user_id == user_id,
                ResumeVariant.job_id == job_id,
            )
            .order_by(ResumeVariant.created_at.desc())
        )
        if existing_variant:
            requirement_summary = self._get_job_requirement_summary(self._get_job(job_id))
            return {
                "rewritten_text": existing_variant.rewritten_text,
                "cached": True,
                "plan": existing_variant.plan,
                "claims": existing_variant.claims or [],
                "validation_results": existing_variant.validation_results or [],
                "target_job_profile": requirement_summary,
            }
        existing = self.db.scalar(
            select(ResumeRewrite).where(ResumeRewrite.user_id == user_id, ResumeRewrite.job_id == job_id)
        )
        if existing:
            requirement_summary = self._get_job_requirement_summary(self._get_job(job_id))
            resume = self._get_active_resume(user_id)
            candidate_graph = self._get_candidate_graph(user_id, resume.id) if resume else None
            plan = self._build_resume_plan(resume, candidate_graph, self._get_job(job_id), requirement_summary) if resume and candidate_graph else {}
            if resume is not None:
                self.db.add(
                    ResumeVariant(
                        user_id=user_id,
                        resume_id=resume.id,
                        job_id=job_id,
                        plan=plan,
                        claims=[],
                        validation_results=[],
                        rewritten_text=existing.rewritten_text,
                    )
                )
                self.db.commit()
            return {
                "rewritten_text": existing.rewritten_text,
                "cached": True,
                "plan": plan,
                "claims": [],
                "validation_results": [],
                "target_job_profile": requirement_summary,
            }
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
        requirement_summary = self._get_job_requirement_summary(job)
        candidate_graph = self._get_candidate_graph(user_id, resume.id)
        plan = self._build_resume_plan(resume, candidate_graph, job, requirement_summary)
        rewritten = self._rewrite_resume_with_groq(
            resume.parsed_text,
            job.job_description,
            requirement_summary,
        )
        claims = self._build_resume_claims(plan, candidate_graph, requirement_summary, rewritten)
        validation_results = self._validate_resume_claims(claims, candidate_graph, requirement_summary)
        record = ResumeRewrite(user_id=user_id, job_id=job_id, rewritten_text=rewritten)
        self.db.add(record)
        self.db.add(
            ResumeVariant(
                user_id=user_id,
                resume_id=resume.id,
                job_id=job_id,
                plan=plan,
                claims=claims,
                validation_results=validation_results,
                rewritten_text=rewritten,
            )
        )
        self.db.commit()
        return {
            "rewritten_text": rewritten,
            "cached": False,
            "plan": plan,
            "claims": claims,
            "validation_results": validation_results,
            "target_job_profile": requirement_summary,
        }

    def create_feedback(self, user_id: UUID, payload) -> dict[str, object]:
        event = FeedbackEvent(user_id=user_id, job_id=payload.job_id, event_type=payload.event_type, payload=payload.payload)
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return self._serialize_feedback(event)

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
        self.db.add(Notification(user_id=user_id, message=f"Application recorded: {job.job_title} @ {job.company_name or 'Unknown'}"))
        self.db.add(FeedbackEvent(user_id=user_id, job_id=job.id, event_type="apply", payload={"match_score": round(score, 4)}))
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
        self.db.add(FeedbackEvent(user_id=user_id, job_id=application.job_id, event_type=status_value, payload={"application_id": str(application_id)}))
        self.db.commit()
        job = self.db.get(Job, application.job_id) if application.job_id else None
        return self._serialize_application(application, job)

    def delete_application(self, user_id: UUID, application_id: UUID) -> None:
        application = self.db.scalar(
            select(Application).where(Application.id == application_id, Application.user_id == user_id)
        )
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
        self.db.delete(application)
        self.db.commit()

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
            self.db.flush()
            market = self._upsert_job_market_profile(job)
            match = self._maybe_score_job_from_embeddings(job)
            self.db.add(market)
            if match is not None:
                self.db.add(match)
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
        cleaned_lines: list[str] = []
        phone_pattern = re.compile(
            r"(?i)\b(?:phone|tel|mobile|whatsapp|contact)\b[:\s-]*([+]?[\d][\d\s().-]{6,}[\d)])"
        )
        digits_only_pattern = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{6,}\d)(?!\w)")
        for line in text.splitlines():
            current = line
            for pattern in BLOCKED_PII_PATTERNS:
                replacement = "[redacted-email]" if pattern.pattern.startswith("\\b[\\w.%+-]+@") else "[redacted-phone]"
                current = pattern.sub(replacement, current)
            current = phone_pattern.sub("[redacted-phone]", current)
            if re.search(r"(?i)\b(?:phone|tel|mobile|whatsapp|contact)\b", line):
                current = digits_only_pattern.sub("[redacted-phone]", current)
            cleaned_lines.append(current)
        return "\n".join(cleaned_lines)

    def _extract_resume_text_profile(self, file_name: str, data: bytes) -> _ResumeTextProfile:
        raw_text = self._extract_text(file_name, data)
        line_count = len([line for line in raw_text.splitlines() if line.strip()])
        pypdf_score = self._score_resume_text(raw_text)
        chosen_text = raw_text
        chosen_source = "pypdf"
        fallback_score: float | None = None
        if pypdf_score < 0.65:
            fallback_text = self._extract_pdfplumber_text(file_name, data)
            fallback_score = self._score_resume_text(fallback_text)
            if fallback_text.strip() and (
                fallback_score >= pypdf_score
                or self._count_title_like_lines(fallback_text) > self._count_title_like_lines(raw_text)
                or len([line for line in fallback_text.splitlines() if line.strip()]) > line_count
            ):
                chosen_text = fallback_text
                chosen_source = "pdfplumber"
        cleaned_text = self._strip_pii(chosen_text)
        return _ResumeTextProfile(
            source=chosen_source,
            raw_text=chosen_text,
            cleaned_text=cleaned_text,
            line_count=line_count,
            title_count=self._count_title_like_lines(chosen_text),
            section_hits=self._count_section_hits(chosen_text),
            char_count=len(chosen_text),
            cleaned_char_count=len(cleaned_text),
            pypdf_score=pypdf_score,
            fallback_score=fallback_score,
        )

    def _extract_pdfplumber_text(self, file_name: str, data: bytes) -> str:
        if not file_name.lower().endswith(".pdf"):
            return self._extract_text(file_name, data)
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(data)) as pdf:
                return "\n".join(page.extract_text(layout=True) or page.extract_text() or "" for page in pdf.pages)
        except Exception:
            return self._extract_text(file_name, data)

    def _score_resume_text(self, text: str) -> float:
        if not text.strip():
            return 0.0
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return 0.0
        section_hits = sum(1 for keyword_set in SECTION_KEYWORDS.values() for keyword in keyword_set if keyword.lower() in text.lower())
        title_hits = self._count_title_like_lines(text)
        word_count = len(text.split())
        score = 0.0
        score += min(word_count / 180.0, 1.0) * 0.35
        score += min(len(lines) / 20.0, 1.0) * 0.25
        score += min(title_hits / 8.0, 1.0) * 0.2
        score += min(section_hits / 10.0, 1.0) * 0.2
        return max(0.0, min(1.0, score))

    def _count_title_like_lines(self, text: str) -> int:
        titles = 0
        for line in text.splitlines():
            stripped = line.strip()
            if len(stripped) < 4:
                continue
            if stripped.isupper() and len(stripped.split()) <= 6:
                titles += 1
            elif re.fullmatch(r"[A-Z][A-Za-z0-9 &/().,-]{2,40}", stripped):
                titles += 1
        return titles

    def _count_section_hits(self, text: str) -> dict[str, int]:
        lowered = text.lower()
        return {
            section: sum(1 for keyword in keywords if keyword in lowered)
            for section, keywords in SECTION_KEYWORDS.items()
        }

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
        query = (
            select(Job)
            .where(Job.is_active.is_(True), Job.embedding.is_not(None))
            .where(cosine_distance <= 1 - settings.match_score_threshold)
        )
        if location:
            query = query.where(Job.location.ilike(f"%{location}%"))
        if company:
            query = query.where(Job.company_name.ilike(f"%{company}%"))
        skill_terms = [term.strip().lower() for term in skills.split(",")] if skills else []
        if skill_terms:
            query = query.where(or_(*(func.lower(Job.job_description).contains(term) for term in skill_terms)))
        return query.order_by(cosine_distance.asc(), Job.ingested_at.desc())

    def _matching_jobs_count(self, user_id: UUID) -> int:
        resume = self._get_active_resume(user_id)
        if resume is None or resume.embedding is None:
            return 0
        query = self._build_job_search_query(resume.embedding, location=None, skills=None, company=None)
        return self.db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0

    def _analyze_resume_with_groq(self, text_profile: _ResumeTextProfile) -> ResumeAnalysisResult:
        cleaned_text = text_profile.cleaned_text
        chunks = self._split_resume_text(cleaned_text)
        diagnostics: dict[str, object] = {"text_source": text_profile.source, "chunk_count": len(chunks)}
        try:
            analyses = [
                self._analyze_resume_chunk(chunk, text_profile, index, len(chunks))
                for index, chunk in enumerate(chunks, start=1)
            ]
            if not analyses:
                raise LLMResponseFormatError("No resume chunks available for analysis.")
            merged = self._merge_chunk_analyses(analyses)
            diagnostics["mode"] = "llm"
            diagnostics["schema_valid"] = True
            self._last_resume_analysis_diagnostics = diagnostics
            return merged
        except (LLMConfigurationError, LLMRequestError, LLMResponseFormatError, Exception) as exc:
            diagnostics["mode"] = "fallback"
            diagnostics["reason"] = type(exc).__name__
            diagnostics["message"] = str(exc)[:500]
            self._last_resume_analysis_diagnostics = diagnostics
            analysis = self._heuristic_resume_analysis(cleaned_text)
            merged = self._merge_resume_analysis(analysis, self._extract_resume_structures(cleaned_text))
            return merged

    def _analyze_resume_chunk(
        self,
        chunk: str,
        text_profile: _ResumeTextProfile,
        chunk_index: int,
        chunk_count: int,
    ) -> ResumeAnalysisResult:
        prompt = (
            "Extract a structured candidate graph from this resume or academic CV chunk.\n"
            "Return only a valid json object. Do not include markdown, commentary, or reasoning.\n"
            "Do not invent facts. Keep every list concise: at most 12 skills, 5 experience items, "
            "5 projects, 5 achievements, 8 publications, and 8 evidence spans. "
            "Do not include skill_evidence unless it adds information beyond skills.\n"
            "Use this exact json shape and exact value types:\n"
            "{\n"
            '  "skills": ["skill name"],\n'
            '  "summary": "concise factual summary",\n'
            '  "experience_highlights": ["role or accomplishment"],\n'
            '  "constraints": {},\n'
            '  "evidence_spans": [{"source":"resume","text":"verbatim source excerpt"}],\n'
            '  "skill_evidence": [],\n'
            '  "experience_facts": [{"title":"","company":null,"description":"",'
            '"evidence":[{"source":"resume","text":"verbatim source excerpt"}]}],\n'
            '  "education": [{"text":"verbatim education item","source":"resume"}],\n'
            '  "projects": [{"text":"verbatim project item","source":"resume"}],\n'
            '  "achievements": [{"text":"verbatim achievement item","source":"resume"}],\n'
            '  "publications": [{"text":"verbatim publication item","source":"resume"}]\n'
            "}\n"
            "All skills and highlights must be strings. All evidence spans must be objects.\n\n"
            f"Document profile:\nsource={text_profile.source}\nchunk={chunk_index}/{chunk_count}\nchar_count={len(chunk)}\n\n"
            f"Resume chunk:\n{chunk}"
        )
        payload = generate_structured_json(
            "You extract structured resume information for a career opportunity engine.",
            prompt,
            response_model=ResumeAnalysisResult,
            extra_params={"max_tokens": 4096},
        )
        return ResumeAnalysisResult.model_validate(payload)

    def _split_resume_text(self, text: str, chunk_size: int = 5000) -> list[str]:
        stripped = text.strip()
        if len(stripped) <= chunk_size:
            return [stripped]
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0
        for paragraph in stripped.splitlines():
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if current_len + len(paragraph) + 1 > chunk_size and current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            current.append(paragraph)
            current_len += len(paragraph) + 1
        if current:
            chunks.append("\n".join(current))
        return chunks or [stripped]

    def _extract_resume_structures(self, cleaned_text: str) -> dict[str, list[dict[str, object]] | list[str]]:
        sections = self._split_by_titles(cleaned_text)
        return {
            "education": self._section_items(sections.get("education", [])),
            "projects": self._section_items(sections.get("projects", [])),
            "achievements": self._section_items(sections.get("achievements", [])),
            "publications": self._section_items(sections.get("publications", [])),
            "experience_highlights": self._section_highlights(sections.get("experience", [])),
        }

    def _split_by_titles(self, text: str) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = defaultdict(list)
        current = "summary"
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            detected = self._detect_resume_section(stripped)
            if detected:
                current = detected
                continue
            sections[current].append(stripped)
        return sections

    def _detect_resume_section(self, line: str) -> str | None:
        lowered = line.lower().strip(":")
        for section, keywords in SECTION_KEYWORDS.items():
            if lowered in keywords or any(lowered.startswith(keyword) for keyword in keywords):
                return section
        return None

    def _section_items(self, lines: list[str]) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for line in lines:
            if len(line) < 4:
                continue
            items.append({"text": line, "source": "resume"})
        return items[:10]

    def _section_highlights(self, lines: list[str]) -> list[str]:
        highlights = [line for line in lines if len(line) > 20][:8]
        return highlights

    def _merge_resume_analysis(
        self,
        primary: ResumeAnalysisResult,
        fallback: dict[str, list[dict[str, object]] | list[str]],
    ) -> ResumeAnalysisResult:
        publications = fallback.get("publications") or []
        experience_highlights = primary.experience_highlights or []
        if not experience_highlights:
            experience_highlights = fallback.get("experience_highlights") or []
        return ResumeAnalysisResult(
            skills=primary.skills,
            summary=primary.summary,
            experience_highlights=experience_highlights,
            constraints=primary.constraints,
            evidence_spans=primary.evidence_spans,
            skill_evidence=primary.skill_evidence,
            experience_facts=primary.experience_facts,
            education=primary.education or fallback.get("education") or [],
            projects=primary.projects or fallback.get("projects") or [],
            achievements=primary.achievements or fallback.get("achievements") or [],
            publications=primary.publications or publications,
        )

    def _merge_chunk_analyses(self, analyses: list[ResumeAnalysisResult]) -> ResumeAnalysisResult:
        if not analyses:
            return ResumeAnalysisResult()
        summary = next((item.summary for item in analyses if item.summary), "")
        skills = self._unique_strings([skill for item in analyses for skill in item.skills])
        experience_highlights = self._unique_strings(
            [highlight for item in analyses for highlight in item.experience_highlights]
        )
        evidence_spans = [span for item in analyses for span in item.evidence_spans]
        skill_evidence = [item for analysis in analyses for item in analysis.skill_evidence]
        experience_facts = [item for analysis in analyses for item in analysis.experience_facts]
        education = [item for analysis in analyses for item in analysis.education]
        projects = [item for analysis in analyses for item in analysis.projects]
        achievements = [item for analysis in analyses for item in analysis.achievements]
        publications = [item for analysis in analyses for item in analysis.publications]
        constraints = self._merge_constraints([analysis.constraints for analysis in analyses])
        if not summary:
            summary = self._derive_heuristic_summary("\n".join(
                span.text for span in evidence_spans if getattr(span, "text", "")
            ))
        return ResumeAnalysisResult(
            skills=skills,
            summary=summary or "Heuristic resume extraction completed.",
            experience_highlights=experience_highlights,
            constraints=constraints,
            evidence_spans=evidence_spans,
            skill_evidence=skill_evidence,
            experience_facts=experience_facts,
            education=education,
            projects=projects,
            achievements=achievements,
            publications=publications,
        )

    def _merge_constraints(self, items: list[dict[str, str | bool | int | float | list[str] | None]]) -> dict[str, object]:
        merged: dict[str, object] = {}
        for item in items:
            for key, value in item.items():
                if value in (None, "", [], {}):
                    continue
                if key not in merged:
                    merged[key] = value
        return merged

    def _unique_strings(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            item = value.strip()
            if not item:
                continue
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            result.append(item)
        return result[:20]

    def _rewrite_resume_with_groq(
        self,
        resume_text: str,
        job_description: str,
        requirement_summary: dict[str, object],
    ) -> str:
        target_context = self._format_requirement_context(requirement_summary)
        prompt = (
            "Rewrite the resume to better fit the target role. "
            "Only rephrase, reorder, and emphasize content already present in the source resume. "
            "Do not add new skills, credentials, or work history.\n"
            'Return ONLY a JSON object with a single key "rewritten_text" whose value is the polished resume body. '
            "Do not include markdown, commentary, or any other keys.\n\n"
            f"Source resume:\n{resume_text}\n\nTarget job description:\n{job_description}"
            f"\n\nCanonical job profile:\n{target_context}"
        )
        try:
            payload = generate_structured_json(
                "You tailor resumes without fabricating experience.",
                prompt,
                response_model=ResumeRewriteResult,
            )
        except (LLMConfigurationError, LLMRequestError, LLMResponseFormatError):
            return self._heuristic_resume_rewrite(resume_text, job_description)
        return ResumeRewriteResult.model_validate(payload).rewritten_text

    def _build_resume_plan(
        self,
        resume: Resume,
        candidate_graph: CandidateGraph,
        job: Job,
        requirement_summary: dict[str, object],
    ) -> dict[str, object]:
        emphasized_skills = list(
            dict.fromkeys(
                [
                    *(resume.extracted_skills or []),
                    *(requirement_summary.get("required_skills") or []),
                    *(requirement_summary.get("preferred_skills") or []),
                ]
            )
        )
        return {
            "section_order": ["summary", "skills", "experience", "projects"],
            "emphasized_skills": emphasized_skills,
            "selected_evidence": self._plan_evidence_spans(candidate_graph, requirement_summary, resume),
            "notes": [
                f"Target role: {job.job_title}",
                f"Occupation family: {requirement_summary.get('occupation_family') or 'General'}",
                f"Transition focus: {self._transition_focus(requirement_summary)}",
            ],
        }

    def _format_requirement_context(self, requirement_summary: dict[str, object]) -> str:
        return (
            f"occupation_family={requirement_summary.get('occupation_family')}; "
            f"seniority={requirement_summary.get('seniority')}; "
            f"required_skills={', '.join(requirement_summary.get('required_skills') or []) or 'none'}; "
            f"preferred_skills={', '.join(requirement_summary.get('preferred_skills') or []) or 'none'}; "
            f"education={', '.join(requirement_summary.get('education_requirements') or []) or 'none'}; "
            f"experience={', '.join(requirement_summary.get('experience_requirements') or []) or 'none'}; "
            f"licenses={', '.join(requirement_summary.get('licenses') or []) or 'none'}; "
            f"salary_confidence={requirement_summary.get('salary_confidence')}; "
            f"freshness_score={requirement_summary.get('freshness_score')}; "
            f"trust_score={requirement_summary.get('trust_score')}"
        )

    def _plan_evidence_spans(
        self,
        candidate_graph: CandidateGraph,
        requirement_summary: dict[str, object],
        resume: Resume,
    ) -> list[dict[str, object]]:
        spans = list(candidate_graph.source_spans or [])
        if not spans and resume.parsed_text:
            spans = [{"source": "resume", "text": resume.parsed_text[:500]}]
        selected: list[dict[str, object]] = []
        required_skills = set(requirement_summary.get("required_skills") or [])
        for item in candidate_graph.skills or []:
            name = str(item.get("name") or "").lower()
            if name and (not required_skills or name in required_skills):
                evidence = item.get("evidence") or spans[:1]
                selected.append(
                    {
                        "source": "candidate_graph",
                        "text": name,
                        "evidence": evidence,
                        "transformation": "evidence_selected",
                    }
                )
        if not selected:
            selected = [
                {
                    "source": span.get("source", "resume"),
                    "text": span.get("text", ""),
                    "transformation": "compressed",
                }
                for span in spans[:3]
            ]
        return selected

    def _build_resume_claims(
        self,
        plan: dict[str, object],
        candidate_graph: CandidateGraph,
        requirement_summary: dict[str, object],
        rewritten: str,
    ) -> list[dict[str, object]]:
        claims: list[dict[str, object]] = []
        emphasized_skills = plan.get("emphasized_skills") or []
        for skill in emphasized_skills[:5]:
            claims.append(
                {
                    "claim": f"Highlights {skill} for the target role",
                    "evidence": self._claim_evidence_for_skill(candidate_graph, str(skill)),
                    "transformation": "emphasized",
                }
            )
        claims.append(
            {
                "claim": rewritten[:220],
                "evidence": (plan.get("selected_evidence") or [])[:2],
                "transformation": "rephrased",
            }
        )
        claims.append(
            {
                "claim": f"Aligned to {requirement_summary.get('occupation_family') or 'General'} profile",
                "evidence": self._claim_evidence_for_requirement(requirement_summary),
                "transformation": "reordered",
            }
        )
        return claims

    def _claim_evidence_for_skill(self, candidate_graph: CandidateGraph, skill: str) -> list[dict[str, object]]:
        evidence: list[dict[str, object]] = []
        for item in candidate_graph.skills or []:
            if str(item.get("name") or "").lower() == skill.lower():
                evidence.extend(item.get("evidence") or [])
        return evidence or (candidate_graph.source_spans or [])[:1]

    def _claim_evidence_for_requirement(self, requirement_summary: dict[str, object]) -> list[dict[str, object]]:
        evidence: list[dict[str, object]] = []
        for key in ("required_skills", "preferred_skills", "education_requirements", "experience_requirements"):
            values = requirement_summary.get(key) or []
            if values:
                evidence.append({"source": "job_profile", "text": ", ".join(str(value) for value in values[:5]), "type": key})
        return evidence

    def _validate_resume_claims(
        self,
        claims: list[dict[str, object]],
        candidate_graph: CandidateGraph,
        requirement_summary: dict[str, object],
    ) -> list[dict[str, object]]:
        evidence_text = " ".join(
            [
                candidate_graph.summary or "",
                " ".join(item.get("name", "") for item in (candidate_graph.skills or []) if isinstance(item, dict)),
                " ".join(str(value) for value in (requirement_summary.get("required_skills") or [])),
                " ".join(str(value) for value in (requirement_summary.get("preferred_skills") or [])),
            ]
        ).lower()
        results: list[dict[str, object]] = []
        for claim in claims:
            claim_text = str(claim.get("claim") or "")
            evidence = claim.get("evidence") or []
            status = "passed" if evidence else "needs_review"
            if claim_text and claim_text.lower().split()[0] not in evidence_text:
                status = "needs_review" if not evidence else status
            results.append(
                {
                    "status": status,
                    "rule": "evidence-backed rewrite",
                    "claim": claim_text,
                    "evidence_count": len(evidence),
                }
            )
        return results

    def _transition_focus(self, requirement_summary: dict[str, object]) -> str:
        required = len(requirement_summary.get("required_skills") or [])
        preferred = len(requirement_summary.get("preferred_skills") or [])
        if required <= 2:
            return "light skill gap"
        if preferred > required:
            return "adjacent skill transfer"
        return "structured skill bridge"

    def _upsert_candidate_graph(
        self,
        user_id: UUID,
        resume_id: UUID,
        analysis: ResumeAnalysisResult,
        cleaned_text: str,
    ) -> CandidateGraph:
        graph = self.db.scalar(
            select(CandidateGraph).where(CandidateGraph.user_id == user_id, CandidateGraph.resume_id == resume_id)
        )
        if graph is None:
            graph = CandidateGraph(user_id=user_id, resume_id=resume_id, summary=analysis.summary)
        graph.summary = analysis.summary
        graph.skills = [skill.model_dump(mode="json") for skill in analysis.skill_evidence] or [
            {"name": skill, "evidence": [{"source": "resume", "text": skill}]} for skill in analysis.skills
        ]
        graph.experience_highlights = analysis.experience_highlights
        graph.experiences = [item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in analysis.experience_facts]
        graph.education = analysis.education
        graph.projects = analysis.projects
        graph.achievements = analysis.achievements
        graph.publications = analysis.publications
        graph.constraints = analysis.constraints
        graph.preferences = graph.preferences or {
            "location": None,
            "work_authorization": None,
            "remote_preference": None,
            "role_families": [],
        }
        graph.source_spans = [item.model_dump(mode="json") for item in analysis.evidence_spans] or [
            {"source": "resume", "text": cleaned_text[:500]}
        ]
        self.db.add(graph)
        self.db.flush()
        return graph

    def _build_parse_diagnostics(
        self,
        text_profile: _ResumeTextProfile,
        analysis: ResumeAnalysisResult,
        graph: CandidateGraph,
        task: ResumeParseTask,
    ) -> dict[str, object]:
        base = dict(self._last_resume_analysis_diagnostics)
        return {
            "text_source": text_profile.source,
            "char_count": text_profile.char_count,
            "cleaned_char_count": text_profile.cleaned_char_count,
            "cleaning_ratio": round(
                text_profile.cleaned_char_count / max(text_profile.char_count, 1), 3
            ),
            "line_count": text_profile.line_count,
            "title_count": text_profile.title_count,
            "section_hits": text_profile.section_hits,
            "pypdf_score": round(text_profile.pypdf_score, 3),
            "fallback_score": round(text_profile.fallback_score, 3) if text_profile.fallback_score is not None else None,
            "analysis_mode": base.get("mode", "unknown"),
            "analysis_reason": base.get("reason"),
            "analysis_message": base.get("message"),
            "chunk_count": base.get("chunk_count"),
            "schema_valid": base.get("schema_valid", True),
            "fallback_used": base.get("mode") != "llm",
            "skill_count": len(analysis.skills),
            "education_count": len(analysis.education),
            "project_count": len(analysis.projects),
            "achievement_count": len(analysis.achievements),
            "publication_count": len(analysis.publications),
            "evidence_count": len(analysis.evidence_spans),
            "graph_id": str(graph.id),
            "task_id": str(task.id),
        }

    def _upsert_job_market_profile(self, job: Job) -> JobMarketProfile:
        profile = self.db.scalar(select(JobMarketProfile).where(JobMarketProfile.job_id == job.id))
        payload = self._extract_job_requirements(job.job_title, job.job_description)
        if profile is None:
            profile = JobMarketProfile(job_id=job.id)
        profile.occupation_family = payload["occupation_family"]
        profile.seniority = payload["seniority"]
        profile.required_skills = payload["required_skills"]
        profile.preferred_skills = payload["preferred_skills"]
        profile.education_requirements = payload["education_requirements"]
        profile.experience_requirements = payload["experience_requirements"]
        profile.licenses = payload["licenses"]
        profile.salary_confidence = payload["salary_confidence"]
        profile.freshness_score = payload["freshness_score"]
        profile.trust_score = payload["trust_score"]
        profile.raw_requirements = payload
        self.db.add(profile)
        self.db.flush()
        return profile

    def _upsert_job_market_profile_payload(
        self, job: Job, payload: dict[str, object]
    ) -> JobMarketProfile:
        profile = self.db.scalar(select(JobMarketProfile).where(JobMarketProfile.job_id == job.id))
        if profile is None:
            profile = JobMarketProfile(job_id=job.id)
        profile.occupation_family = str(payload.get("occupation_family") or "General")
        profile.seniority = str(payload.get("seniority") or "mid")
        profile.required_skills = [str(item) for item in (payload.get("required_skills") or [])]
        profile.preferred_skills = [str(item) for item in (payload.get("preferred_skills") or [])]
        profile.education_requirements = [
            str(item) for item in (payload.get("education_requirements") or [])
        ]
        profile.experience_requirements = [
            str(item) for item in (payload.get("experience_requirements") or [])
        ]
        profile.licenses = [str(item) for item in (payload.get("licenses") or [])]
        profile.salary_confidence = str(payload.get("salary_confidence") or "C")
        profile.freshness_score = float(payload.get("freshness_score") or 1.0)
        profile.trust_score = float(payload.get("trust_score") or 0.75)
        profile.raw_requirements = payload
        self.db.add(profile)
        self.db.flush()
        return profile

    def _extract_job_requirements(self, job_title: str, job_description: str) -> dict[str, object]:
        lowered = f"{job_title} {job_description}".lower()
        required = [skill for skill in sorted(SKILL_KEYWORDS) if skill in lowered]
        preferred = [skill for skill in ["docker", "aws", "graphql", "testing", "typescript"] if skill in lowered and skill not in required]
        return {
            "occupation_family": "Engineering" if "engineer" in lowered or "developer" in lowered else "General",
            "seniority": "mid" if "senior" not in lowered else "senior",
            "required_skills": required,
            "preferred_skills": preferred,
            "education_requirements": ["bachelor degree"] if "bachelor" in lowered or "degree" in lowered else [],
            "experience_requirements": ["2+ years"] if "years" in lowered or "experience" in lowered else [],
            "licenses": [],
            "salary_confidence": "A" if any(keyword in lowered for keyword in ["salary", "$", "compensation"]) else "C",
            "freshness_score": 1.0,
            "trust_score": 0.8,
        }

    def _get_job_requirement_summary(self, job: Job) -> dict[str, object]:
        market = self.db.scalar(select(JobMarketProfile).where(JobMarketProfile.job_id == job.id))
        payload = market.raw_requirements if market and market.raw_requirements else self._extract_job_requirements(job.job_title, job.job_description)
        return {
            "required_skills": list((market.required_skills if market else payload.get("required_skills", [])) or []),
            "preferred_skills": list((market.preferred_skills if market else payload.get("preferred_skills", [])) or []),
            "education_requirements": list((market.education_requirements if market else payload.get("education_requirements", [])) or []),
            "experience_requirements": list((market.experience_requirements if market else payload.get("experience_requirements", [])) or []),
            "licenses": list((market.licenses if market else payload.get("licenses", [])) or []),
            "occupation_family": market.occupation_family if market else payload.get("occupation_family"),
            "seniority": market.seniority if market else payload.get("seniority"),
            "salary_confidence": market.salary_confidence if market else payload.get("salary_confidence", "C"),
            "freshness_score": market.freshness_score if market else payload.get("freshness_score", 1.0),
            "trust_score": market.trust_score if market else payload.get("trust_score", 0.75),
            "raw_requirements": payload,
        }

    def _score_job(self, user_id: UUID, job: Job, resume: Resume) -> _OpportunityParts:
        graph = self._get_candidate_graph(user_id, resume.id)
        market = self.db.scalar(select(JobMarketProfile).where(JobMarketProfile.job_id == job.id))
        candidate_skills = {item["name"].lower() for item in (graph.skills or []) if item.get("name")}
        required_skills = set(market.required_skills or job.skill_tags or [])
        preferred_skills = set(market.preferred_skills or [])
        exact = len(candidate_skills & required_skills)
        transferable = len(candidate_skills & preferred_skills)
        total_required = max(len(required_skills), 1)
        attainability = min(1.0, (exact + transferable * 0.6) / total_required)
        salary = self._annualized_salary(job.mid_salary_sgd, job.pay_period) or 0.0
        salary_advantage = min(1.0, salary / 120000.0) if salary else 0.25
        demand = 0.85 if market and market.freshness_score > 0.8 else 0.65
        entry_barrier = max(0.0, 1.0 - attainability)
        career_option = 0.7 if market and market.occupation_family == "Engineering" else 0.6
        preference_fit = 0.8 if not graph.preferences or not graph.preferences.get("location") else 0.7
        data_confidence = market.trust_score if market else 0.7
        fit = (
            0.30 * salary_advantage
            + 0.25 * attainability
            + 0.15 * demand
            + 0.10 * (1.0 - entry_barrier)
            + 0.10 * career_option
            + 0.05 * preference_fit
            + 0.05 * data_confidence
        )
        category = "easy_win" if fit >= 0.75 and entry_barrier < 0.35 else "high_potential" if fit >= 0.58 else "stretch"
        transition_difficulty = "low" if entry_barrier < 0.25 else "moderate" if entry_barrier < 0.55 else "high"
        rationale = []
        if exact:
            rationale.append(f"{exact} direct skill matches")
        if transferable:
            rationale.append(f"{transferable} adjacent skills transfer")
        if salary:
            rationale.append(f"Salary signal around SGD {salary:,.0f}")
        if market and market.occupation_family:
            rationale.append(f"Occupation family: {market.occupation_family}")
        vector = OpportunityScoreVector(
            salary_advantage=round(salary_advantage, 3),
            attainability=round(attainability, 3),
            demand=round(demand, 3),
            entry_barrier=round(entry_barrier, 3),
            career_option=round(career_option, 3),
            preference_fit=round(preference_fit, 3),
            data_confidence=round(data_confidence, 3),
            fit=round(fit, 3),
        )
        breakdown = {
            "salary_advantage": round(salary_advantage, 3),
            "attainability": round(attainability, 3),
            "demand": round(demand, 3),
            "entry_barrier": round(entry_barrier, 3),
            "career_option": round(career_option, 3),
            "preference_fit": round(preference_fit, 3),
            "data_confidence": round(data_confidence, 3),
        }
        return _OpportunityParts(
            score=round(fit, 3),
            category=category,
            vector=vector,
            breakdown=breakdown,
            rationale=rationale,
            transition_difficulty=transition_difficulty,
            data_confidence=round(data_confidence, 3),
        )

    def _maybe_score_job_from_embeddings(self, job: Job) -> CandidateJobMatch | None:
        return None

    def _heuristic_resume_analysis(self, cleaned_text: str) -> ResumeAnalysisResult:
        lowered = cleaned_text.lower()
        skills = [skill for skill in sorted(SKILL_KEYWORDS) if skill in lowered]
        summary = self._derive_heuristic_summary(cleaned_text)
        evidence_text = cleaned_text[:400]
        return ResumeAnalysisResult(
            skills=skills,
            summary=summary or "Heuristic resume extraction completed.",
            experience_highlights=[line.strip("-• ").strip() for line in cleaned_text.splitlines() if len(line.strip()) > 20][:5],
            constraints={},
            evidence_spans=[{"source": "resume", "text": evidence_text}],
            skill_evidence=[
                {"name": skill, "evidence": [{"source": "resume", "text": skill}]} for skill in skills[:12]
            ],
            experience_facts=[],
            education=[],
            projects=[],
            achievements=[],
        )

    def _derive_heuristic_summary(self, cleaned_text: str) -> str:
        lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
        if not lines:
            return ""
        candidate_lines = lines[1:10] if len(lines) > 1 else lines
        for line in candidate_lines:
            lowered = line.lower()
            if len(line) >= 24 and not lowered.startswith(("tel", "phone", "email", "education")):
                return line[:220]
        return lines[0][:220]

    def _heuristic_resume_rewrite(self, resume_text: str, job_description: str) -> str:
        headline = resume_text.splitlines()[0].strip() if resume_text.splitlines() else "Candidate Summary"
        return (
            f"{headline}\n\n"
            f"Targeted for: {job_description[:180].strip()}\n\n"
            f"Selected experience:\n{resume_text[:1500].strip()}"
        ).strip()

    def _serialize_match(self, match: _OpportunityParts | CandidateJobMatch) -> dict[str, object]:
        if isinstance(match, CandidateJobMatch):
            score = match.opportunity_score
            category = match.category
            breakdown = match.fit_breakdown
            rationale = match.rationale
            transition_difficulty = match.transition_difficulty
            data_confidence = match.data_confidence
        else:
            score = match.score
            category = match.category
            breakdown = match.breakdown
            rationale = match.rationale
            transition_difficulty = match.transition_difficulty
            data_confidence = match.data_confidence
        return {
            "opportunity_score": score,
            "opportunity_category": category,
            "fit_breakdown": breakdown,
            "rationale": rationale,
            "transition_difficulty": transition_difficulty,
            "data_confidence": data_confidence,
        }

    def _compute_transfer_notes(self, job: Job, resume: Resume, match: _OpportunityParts) -> list[str]:
        resume_skills = set(resume.extracted_skills or [])
        job_skills = set(job.skill_tags or [])
        transferables = sorted(resume_skills & job_skills)
        return [f"{skill} is already present in the resume" for skill in transferables[:3]] or [
            "Existing experience can be reframed toward the target role."
        ]

    def _compute_gap_notes(self, job: Job, resume: Resume, match: _OpportunityParts) -> list[str]:
        job_skills = set(job.skill_tags or [])
        resume_skills = set(resume.extracted_skills or [])
        gaps = sorted(job_skills - resume_skills)
        return [f"Consider evidence for {skill}" for skill in gaps[:3]] or [
            "Core requirements appear covered by the current profile."
        ]

    def _salary_context(self, job: Job) -> dict[str, object]:
        annual = self._annualized_salary(job.mid_salary_sgd, job.pay_period)
        return {
            "annual_salary_sgd": round(annual, 2) if annual else None,
            "salary_confidence": "A" if job.mid_salary_sgd else "C",
        }

    def _serialize_job(
        self,
        job: Job,
        *,
        user_id: UUID | None = None,
        resume: Resume | None = None,
        match: _OpportunityParts | CandidateJobMatch | None = None,
    ) -> dict[str, object]:
        data = {
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
        if resume is not None and user_id is not None:
            match = match or self._score_job(user_id, job, resume)
            data.update(self._serialize_match(match))
            data["match_score"] = round(self._match_score(resume.embedding, job.embedding), 4)
        return data

    def _serialize_resume(self, resume: Resume, graph: CandidateGraph | None = None) -> dict[str, object]:
        graph_data = self._serialize_candidate_graph(graph) if graph is not None else None
        parse_task = self.db.scalar(
            select(ResumeParseTask)
            .where(ResumeParseTask.resume_id == resume.id)
            .order_by(ResumeParseTask.created_at.desc())
        )
        return {
            "id": resume.id,
            "user_id": resume.user_id,
            "file_name": resume.file_name,
            "file_url": resume.file_url,
            "parsed_text": resume.parsed_text,
            "extracted_skills": resume.extracted_skills or [],
            "candidate_graph": graph_data,
            "embedding_ready": bool(resume.embedding),
            "parse_status": parse_task.status if parse_task else "uploaded",
            "parse_progress": parse_task.progress if parse_task else 0,
            "parse_stage": parse_task.stage if parse_task else "uploaded",
            "parse_error": parse_task.error_message if parse_task else None,
            "parse_task_id": parse_task.id if parse_task else None,
            "parse_mode": self._parse_mode_from_task(parse_task),
            "parse_diagnostics": parse_task.diagnostics if parse_task else None,
            "is_active": resume.is_active,
            "created_at": resume.created_at,
            "updated_at": resume.updated_at,
        }

    def _serialize_resume_parse_task(self, task: ResumeParseTask) -> dict[str, object]:
        return {
            "id": task.id,
            "resume_id": task.resume_id,
            "status": task.status,
            "stage": task.stage,
            "progress": task.progress,
            "error_message": task.error_message,
            "diagnostics": task.diagnostics,
            "attempts": task.attempts,
            "worker_id": task.worker_id,
            "started_at": task.started_at,
            "finished_at": task.finished_at,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }

    def _serialize_resume_tailoring_task(self, task: ResumeTailoringTask) -> dict[str, object]:
        job = self.db.get(Job, task.job_id)
        resume = self.db.get(Resume, task.resume_id)
        return {
            "id": task.id, "user_id": task.user_id, "resume_id": task.resume_id, "job_id": task.job_id,
            "job_title": job.job_title if job else None, "company_name": job.company_name if job else None,
            "source_file_name": resume.file_name if resume else None, "status": task.status, "stage": task.stage,
            "progress": task.progress, "error_message": task.error_message, "attempts": task.attempts,
            "created_at": task.created_at, "updated_at": task.updated_at, "finished_at": task.finished_at,
            "variant": self._serialize_resume_variant(
                self.db.scalar(
                    select(ResumeVariant)
                    .where(ResumeVariant.user_id == task.user_id, ResumeVariant.job_id == task.job_id)
                    .order_by(ResumeVariant.created_at.desc())
                ),
                include_source_file=True,
            ) if task.status == "completed" else None,
        }

    def _serialize_candidate_graph(self, graph: CandidateGraph) -> dict[str, object]:
        return {
            "id": graph.id,
            "user_id": graph.user_id,
            "resume_id": graph.resume_id,
            "summary": graph.summary,
            "skills": graph.skills or [],
            "experience_highlights": graph.experience_highlights or [],
            "experiences": graph.experiences or [],
            "education": graph.education or [],
            "projects": graph.projects or [],
            "achievements": graph.achievements or [],
            "publications": graph.publications or [],
            "constraints": graph.constraints or {},
            "preferences": graph.preferences or {},
            "source_spans": graph.source_spans or [],
            "user_confirmed": graph.user_confirmed,
            "created_at": graph.created_at,
            "updated_at": graph.updated_at,
        }

    def _serialize_feedback(self, event: FeedbackEvent) -> dict[str, object]:
        return {
            "id": event.id,
            "user_id": event.user_id,
            "job_id": event.job_id,
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": event.created_at,
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

    def _serialize_resume_variant(
        self, variant: ResumeVariant | None, *, include_source_file: bool = False
    ) -> dict[str, object] | None:
        if variant is None:
            return None
        job = self.db.get(Job, variant.job_id)
        target_profile = self._get_job_requirement_summary(job) if job else None
        payload = {
            "id": variant.id,
            "user_id": variant.user_id,
            "resume_id": variant.resume_id,
            "job_id": variant.job_id,
            "job_title": job.job_title if job else None,
            "company_name": job.company_name if job else None,
            "plan": variant.plan or {},
            "claims": variant.claims or [],
            "validation_results": variant.validation_results or [],
            "resume_sections": variant.resume_sections or {},
            "change_summary": variant.change_summary or [],
            "evidence_used": variant.evidence_used or [],
            "target_requirements": variant.target_requirements or [],
            "rewritten_text": variant.rewritten_text,
            "target_job_profile": target_profile,
            "created_at": variant.created_at,
        }
        if include_source_file:
            resume = self.db.get(Resume, variant.resume_id) if variant.resume_id else None
            payload["source_file_name"] = resume.file_name if resume else None
            payload["cached"] = True
        return payload

    def _get_candidate_graph(
        self, user_id: UUID, resume_id: UUID | None = None, *, create_if_missing: bool = True
    ) -> CandidateGraph | None:
        statement = select(CandidateGraph).where(CandidateGraph.user_id == user_id)
        if resume_id is not None:
            statement = statement.where(CandidateGraph.resume_id == resume_id)
        statement = statement.order_by(CandidateGraph.created_at.desc())
        graph = self.db.scalar(statement)
        if graph is None:
            if not create_if_missing:
                return None
            active_resume = self._get_active_resume(user_id)
            if active_resume is None:
                return None
            graph = CandidateGraph(
                user_id=user_id,
                resume_id=resume_id or active_resume.id,
                summary="",
                skills=[],
                experiences=[],
                education=[],
                projects=[],
                achievements=[],
                publications=[],
                constraints={},
                preferences={},
                source_spans=[],
                user_confirmed=False,
            )
            self.db.add(graph)
            self.db.flush()
        return graph

    def _parse_mode_from_task(self, task: ResumeParseTask | None) -> str:
        if task is None or not task.diagnostics:
            return "unknown"
        return str(task.diagnostics.get("analysis_mode") or task.diagnostics.get("mode") or "unknown")

    def _get_resume_variant(self, user_id: UUID, resume_id: UUID) -> ResumeVariant | None:
        return self.db.scalar(
            select(ResumeVariant)
            .where(ResumeVariant.user_id == user_id, ResumeVariant.resume_id == resume_id)
            .order_by(ResumeVariant.created_at.desc())
        )

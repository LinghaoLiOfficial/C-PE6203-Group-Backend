from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.career_intelligence import CandidateGraph, JobMarketProfile, ResumeTailoringTask
from app.models.job import Job
from app.models.resume import Resume
from app.models.resume_parse_task import ResumeParseTask


def _vector() -> list[float]:
    return [0.1] * 384


def test_upload_resume_only_registers_file(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    from app.services import job_portal_service

    monkeypatch.setattr(job_portal_service, "embed_text", lambda _: _vector())

    response = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.txt", b"Backend engineer with Python and FastAPI", "text/plain")},
    )

    assert response.status_code == 201
    resume_id = response.json()["resume_id"]
    assert response.json()["status"] == "uploaded"
    assert db_session.query(CandidateGraph).filter(CandidateGraph.resume_id == resume_id).count() == 0
    assert db_session.query(ResumeParseTask).filter(ResumeParseTask.resume_id == resume_id).count() == 0


def test_resume_parse_runs_in_worker_and_reports_completion(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    from app.services import job_portal_service
    from app.services.generation_queue_service import GenerationQueueService

    monkeypatch.setattr(job_portal_service, "embed_text", lambda _: _vector())
    response = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.txt", b"Backend engineer with Python and FastAPI", "text/plain")},
    )
    resume_id = response.json()["resume_id"]

    parse_response = client.post(f"/api/v1/resumes/{resume_id}/parse")
    assert parse_response.status_code == 202
    task_id = parse_response.json()["id"]
    assert parse_response.json()["status"] == "queued"

    assert GenerationQueueService(db_session).run_once("test-worker") == task_id

    status_response = client.get(f"/api/v1/resumes/{resume_id}/parse-status")
    assert status_response.status_code == 200
    assert status_response.json()["task"]["status"] == "completed"
    graph = db_session.query(CandidateGraph).filter(CandidateGraph.resume_id == resume_id).one()
    assert graph.summary
    assert {item["name"] for item in graph.skills} >= {"fastapi", "python"}
    assert graph.experience_highlights is not None


def test_failed_resume_parse_can_be_retried(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    from app.services import job_portal_service
    from app.services.generation_queue_service import GenerationQueueService

    monkeypatch.setattr(job_portal_service.JobPortalService, "_analyze_resume_with_groq", lambda *_: (_ for _ in ()).throw(RuntimeError("parse boom")))
    response = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.txt", b"Backend engineer", "text/plain")},
    )
    resume_id = response.json()["resume_id"]
    first = client.post(f"/api/v1/resumes/{resume_id}/parse")
    assert first.status_code == 202

    try:
        GenerationQueueService(db_session).run_once("test-worker")
    except RuntimeError:
        pass

    status_response = client.get(f"/api/v1/resumes/{resume_id}/parse-status")
    assert status_response.json()["task"]["status"] == "failed"
    assert "parse boom" in status_response.json()["task"]["error_message"]

    second = client.post(f"/api/v1/resumes/{resume_id}/parse")
    assert second.status_code == 202
    assert second.json()["id"] != first.json()["id"]


def test_opportunity_map_returns_ranked_sections(
    client: TestClient, db_session: Session, test_user
) -> None:
    resume = Resume(
        user_id=test_user.id,
        file_name="resume.txt",
        file_url="/tmp/resume.txt",
        parsed_text="Python FastAPI PostgreSQL",
        extracted_skills=["python", "fastapi", "postgresql"],
        embedding=_vector(),
        is_active=True,
    )
    job = Job(
        id=uuid4(),
        job_title="Backend Engineer",
        job_description="Build Python and FastAPI services with PostgreSQL.",
        company_name="Example Co",
        location="Remote",
        source="test",
        external_id="backend-1",
        external_apply_url="https://example.com/jobs/backend-1",
        embedding=_vector(),
        skill_tags=["python", "fastapi", "postgresql"],
        is_active=True,
    )
    db_session.add_all([resume, job])
    db_session.flush()
    db_session.add(
        CandidateGraph(
            user_id=test_user.id,
            resume_id=resume.id,
            summary="Backend engineer",
            skills=[{"name": "python"}, {"name": "fastapi"}, {"name": "postgresql"}],
            preferences={},
            constraints={},
            source_spans=[{"source": "resume", "text": "Python FastAPI PostgreSQL"}],
        )
    )
    db_session.add(
        JobMarketProfile(
            job_id=job.id,
            occupation_family="Engineering",
            required_skills=["python", "fastapi", "postgresql"],
            preferred_skills=[],
            freshness_score=1.0,
            trust_score=0.9,
        )
    )
    db_session.commit()

    response = client.get("/api/v1/opportunities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sections"]
    assert payload["sections"][0]["jobs"][0]["job_title"] == "Backend Engineer"
    assert payload["sections"][0]["jobs"][0]["fit_breakdown"]["attainability"] == 1.0


def test_feedback_event_persists(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/feedback", json={"event_type": "dismiss", "payload": {"reason": "low salary"}})

    assert response.status_code == 201
    assert response.json()["event_type"] == "dismiss"


def test_job_detail_exposes_canonical_profile(
    client: TestClient, db_session: Session, test_user
) -> None:
    job = Job(
        id=uuid4(),
        job_title="Backend Engineer",
        job_description="Build Python and FastAPI services with PostgreSQL.",
        company_name="Example Co",
        location="Remote",
        source="test",
        external_id="backend-detail",
        external_apply_url="https://example.com/jobs/backend-detail",
        embedding=_vector(),
        skill_tags=["python", "fastapi", "postgresql"],
        is_active=True,
    )
    db_session.add(job)
    db_session.flush()
    db_session.add(
        JobMarketProfile(
            job_id=job.id,
            occupation_family="Engineering",
            seniority="mid",
            required_skills=["python", "fastapi", "postgresql"],
            preferred_skills=["docker"],
            freshness_score=1.0,
            trust_score=0.9,
            raw_requirements={"required_skills": ["python", "fastapi", "postgresql"]},
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/jobs/{job.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["canonical_job_profile"]["occupation_family"] == "Engineering"
    assert payload["canonical_job_profile"]["required_skills"] == ["python", "fastapi", "postgresql"]


def test_rewrite_job_returns_plan_and_validation(
    client: TestClient, db_session: Session, test_user
) -> None:
    resume = Resume(
        user_id=test_user.id,
        file_name="resume.txt",
        file_url="/tmp/resume.txt",
        parsed_text="Python FastAPI PostgreSQL",
        extracted_skills=["python", "fastapi", "postgresql"],
        embedding=_vector(),
        is_active=True,
    )
    job = Job(
        id=uuid4(),
        job_title="Backend Engineer",
        job_description="Build Python and FastAPI services with PostgreSQL.",
        company_name="Example Co",
        location="Remote",
        source="test",
        external_id="backend-rewrite",
        external_apply_url="https://example.com/jobs/backend-rewrite",
        embedding=_vector(),
        skill_tags=["python", "fastapi", "postgresql"],
        is_active=True,
    )
    db_session.add_all([resume, job])
    db_session.flush()
    db_session.add(
        JobMarketProfile(
            job_id=job.id,
            occupation_family="Engineering",
            seniority="mid",
            required_skills=["python", "fastapi", "postgresql"],
            preferred_skills=["docker"],
            freshness_score=1.0,
            trust_score=0.9,
            raw_requirements={"required_skills": ["python", "fastapi", "postgresql"]},
        )
    )
    db_session.commit()

    response = client.post(f"/api/v1/jobs/{job.id}/rewrite")

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert db_session.query(ResumeTailoringTask).filter_by(id=payload["id"]).count() == 1


def test_resume_variant_list_returns_persisted_tailored_resumes(
    client: TestClient, db_session: Session, test_user, monkeypatch
) -> None:
    from app.services import job_portal_service
    from app.schemas.ai import TailoredResumeResult

    monkeypatch.setattr(
        job_portal_service.JobPortalService,
        "_generate_tailored_resume",
        lambda *_: TailoredResumeResult(
            rewritten_text="Backend Engineer\nPython FastAPI PostgreSQL",
            resume={"summary": "Backend Engineer"},
            change_summary=[{"section": "summary", "action": "rephrased", "reason": "Aligned", "source_evidence": ["Python"]}],
            evidence_used=[{"source": "resume", "text": "Python"}],
            target_requirements=[{"requirement": "Python", "matched_evidence": ["Python"], "coverage": "strong"}],
        ),
    )

    monkeypatch.setattr(job_portal_service, "embed_text", lambda _: _vector())
    resume = Resume(
        user_id=test_user.id,
        file_name="resume.txt",
        file_url="/tmp/resume.txt",
        parsed_text="Python FastAPI PostgreSQL",
        extracted_skills=["python", "fastapi", "postgresql"],
        embedding=_vector(),
        is_active=True,
    )
    job = Job(
        id=uuid4(),
        job_title="Backend Engineer",
        job_description="Build Python and FastAPI services with PostgreSQL.",
        company_name="Example Co",
        location="Remote",
        source="test",
        external_id="backend-variants",
        external_apply_url="https://example.com/jobs/backend-variants",
        embedding=_vector(),
        skill_tags=["python", "fastapi", "postgresql"],
        is_active=True,
    )
    db_session.add_all([resume, job])
    db_session.flush()
    db_session.add(
        JobMarketProfile(
            job_id=job.id,
            occupation_family="Engineering",
            seniority="mid",
            required_skills=["python", "fastapi", "postgresql"],
            preferred_skills=["docker"],
            freshness_score=1.0,
            trust_score=0.9,
            raw_requirements={"required_skills": ["python", "fastapi", "postgresql"]},
        )
    )
    db_session.commit()

    rewrite_response = client.post(f"/api/v1/jobs/{job.id}/rewrite")
    assert rewrite_response.status_code == 202
    task_id = rewrite_response.json()["id"]

    from app.services.generation_queue_service import GenerationQueueService

    assert GenerationQueueService(db_session).run_once("test-worker") == task_id

    variants_response = client.get("/api/v1/resumes/variants")
    assert variants_response.status_code == 200
    payload = variants_response.json()
    assert payload[0]["job_id"] == str(job.id)
    assert payload[0]["rewritten_text"]
    assert payload[0]["source_file_name"] == "resume.txt"


def test_tailored_list_includes_queued_task_and_deduplicates_running_task(
    client: TestClient, db_session: Session, test_user
) -> None:
    resume = Resume(
        user_id=test_user.id, file_name="resume.txt", file_url="/tmp/resume.txt",
        parsed_text="Python", is_active=True,
    )
    job = Job(
        id=uuid4(), job_title="Backend Engineer", job_description="Build APIs", company_name="Example",
        location="Remote", source="test", external_id="queued-task",
        external_apply_url="https://example.com/jobs/queued-task", is_active=True,
    )
    db_session.add_all([resume, job])
    db_session.commit()
    response = client.post(f"/api/v1/jobs/{job.id}/rewrite")
    assert response.status_code == 202
    listed = client.get("/api/v1/resumes/tailored")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["status"] == "queued"

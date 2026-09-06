from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.career_intelligence import CandidateGraph
from app.models.resume import Resume
from app.models.resume_parse_task import ResumeParseTask
from app.services.job_portal_service import JobPortalService


def _vector() -> list[float]:
    return [0.1] * 384


def test_delete_resume_removes_database_row_and_file(
    client: TestClient, db_session: Session, test_user, tmp_path: Path
) -> None:
    resume_dir = tmp_path / "resumes" / str(test_user.id)
    resume_dir.mkdir(parents=True)
    file_path = resume_dir / "resume.pdf"
    file_path.write_bytes(b"resume content")

    resume = Resume(
        user_id=test_user.id,
        file_name="resume.pdf",
        file_url=str(file_path),
        parsed_text="Python FastAPI",
        extracted_skills=["Python", "FastAPI"],
        is_active=True,
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    delete_response = client.delete(f"/api/v1/resumes/{resume.id}")

    assert delete_response.status_code == 204
    assert not file_path.exists()
    assert db_session.query(Resume).filter(Resume.id == resume.id).count() == 0


def test_strip_pii_preserves_doi_and_numeric_identifiers(db_session: Session, test_user) -> None:
    service = JobPortalService(db_session)
    text = (
        "Paper DOI: 10.1145/1234567.1234568\n"
        "Conference paper no. 2024-08-31\n"
        "Email: demo@example.com\n"
        "Tel: +65 9123 4567\n"
    )

    cleaned = service._strip_pii(text)

    assert "10.1145/1234567.1234568" in cleaned
    assert "2024-08-31" in cleaned
    assert "[redacted-email]" in cleaned
    assert "[redacted-phone]" in cleaned


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
    assert status_response.json()["task"]["diagnostics"]["analysis_mode"] in {"llm", "fallback"}
    graph = db_session.query(CandidateGraph).filter(CandidateGraph.resume_id == resume_id).one()
    assert graph.summary
    assert {item["name"] for item in graph.skills} >= {"fastapi", "python"}
    assert graph.experience_highlights is not None


def test_failed_resume_parse_keeps_fallback_diagnostics(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    from app.services import job_portal_service
    from app.services.generation_queue_service import GenerationQueueService

    monkeypatch.setattr(
        job_portal_service.JobPortalService,
        "_analyze_resume_with_groq",
        lambda *_: (_ for _ in ()).throw(RuntimeError("parse boom")),
    )
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
    assert status_response.status_code == 200
    assert status_response.json()["task"]["status"] == "failed"
    assert "parse boom" in status_response.json()["task"]["error_message"]


def test_resume_parse_status_exposes_parse_task_diagnostics(
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
    db_session.add(resume)
    db_session.flush()
    task = ResumeParseTask(
        resume_id=resume.id,
        user_id=test_user.id,
        status="completed",
        stage="completed",
        progress=100,
        diagnostics={
            "analysis_mode": "fallback",
            "text_source": "pdfplumber",
            "evidence_count": 4,
            "fallback_used": True,
        },
    )
    db_session.add(task)
    db_session.commit()

    response = client.get(f"/api/v1/resumes/{resume.id}/parse-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task"]["diagnostics"]["analysis_mode"] == "fallback"
    assert payload["task"]["diagnostics"]["text_source"] == "pdfplumber"

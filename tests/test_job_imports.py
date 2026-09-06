from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.career_intelligence import JobMarketProfile
from app.models.job import Job
from app.models.job_import import JobImportBatch, JobImportRow


def _csv_bytes(rows: str) -> bytes:
    return rows.encode("utf-8")


def _vector() -> list[float]:
    return [0.1] * 384


def test_preview_job_import_creates_batch_and_rows(
    admin_client: TestClient, db_session: Session
) -> None:
    csv_data = (
        "job_title,company_name,city_location,country_location,job_description\n"
        "Backend Engineer,Acme,Singapore,Singapore,Build APIs"
    )
    response = admin_client.post(
        "/api/v1/admin/job-imports/preview",
        files={"file": ("jobs.csv", _csv_bytes(csv_data), "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["batch"]["total_rows"] == 1
    assert payload["batch"]["pending_insert_rows"] == 1
    assert db_session.query(JobImportBatch).count() == 1
    assert db_session.query(JobImportRow).count() == 1
    assert payload["batch"]["rows"][0]["canonical_job_profile"]["occupation_family"] == "Engineering"


def test_confirm_job_import_upserts_and_builds_market_profile(
    admin_client: TestClient, db_session: Session, monkeypatch
) -> None:
    from app.services import job_import_service

    monkeypatch.setattr(job_import_service, "embed_text", lambda _: _vector())
    csv_data = (
        "job_title,company_name,city_location,country_location,job_description,"
        "external_apply_url\n"
        "Backend Engineer,Acme,Singapore,Singapore,Build APIs,https://example.com/jobs/1"
    )
    preview = admin_client.post(
        "/api/v1/admin/job-imports/preview",
        files={"file": ("jobs.csv", _csv_bytes(csv_data), "text/csv")},
    )
    batch_id = preview.json()["batch"]["id"]

    confirm = admin_client.post("/api/v1/admin/job-imports/confirm", json={"batch_id": batch_id})

    assert confirm.status_code == 200
    payload = confirm.json()
    assert payload["batch"]["status"] == "imported"
    assert db_session.query(Job).filter(Job.job_title == "Backend Engineer").count() == 1
    job = db_session.query(Job).filter(Job.job_title == "Backend Engineer").one()
    assert job.embedding is not None
    assert db_session.query(JobMarketProfile).filter(JobMarketProfile.job_id == job.id).count() == 1
    assert payload["batch"]["rows"][0]["canonical_job_profile"]["required_skills"] == ["python", "fastapi"]


def test_import_dedupes_same_normalized_key(
    admin_client: TestClient, db_session: Session, monkeypatch
) -> None:
    from app.services import job_import_service

    monkeypatch.setattr(job_import_service, "embed_text", lambda _: _vector())
    existing = Job(
        id=uuid4(),
        job_title="backend engineer",
        job_description="Old desc",
        company_name="Acme",
        city_location="Singapore",
        country_location="Singapore",
        source="admin_csv",
        external_id="existing",
        external_apply_url="https://example.com/jobs/existing",
        is_active=True,
    )
    db_session.add(existing)
    db_session.commit()

    csv_data = (
        "job_title,company_name,city_location,country_location,job_description,"
        "external_apply_url\n"
        "Backend Engineer,Acme,Singapore,Singapore,New desc,https://example.com/jobs/1"
    )
    preview = admin_client.post(
        "/api/v1/admin/job-imports/preview",
        files={"file": ("jobs.csv", _csv_bytes(csv_data), "text/csv")},
    )
    batch_id = preview.json()["batch"]["id"]
    confirm = admin_client.post("/api/v1/admin/job-imports/confirm", json={"batch_id": batch_id})

    assert confirm.status_code == 200
    db_session.expire_all()
    job = db_session.query(Job).filter(Job.company_name == "Acme").one()
    assert job.job_description == "New desc"

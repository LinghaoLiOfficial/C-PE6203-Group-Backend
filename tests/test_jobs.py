from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.job import Job


def test_list_jobs_returns_all_active_jobs_without_resume(
    client: TestClient, db_session: Session
) -> None:
    db_session.add_all(
        [
            Job(
                id=uuid4(),
                job_title="Backend Developer",
                job_description="Build backend services.",
                company_name="Example Co",
                location="Singapore",
                source="job_market_csv",
                external_id="1",
                external_apply_url="https://example.com/jobs/1",
                is_active=True,
            ),
            Job(
                id=uuid4(),
                job_title="Inactive Job",
                job_description="Should not be shown.",
                company_name="Example Co",
                location="Singapore",
                source="job_market_csv",
                external_id="2",
                external_apply_url="https://example.com/jobs/2",
                is_active=False,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["job_title"] == "Backend Developer"


def test_job_serialization_includes_csv_fields(db_session: Session) -> None:
    job = Job(
        id=uuid4(),
        job_title="Data Engineer",
        job_description="Build pipelines.",
        source_id=42,
        company_name="Example Co",
        location="Singapore, Singapore",
        city_location="Singapore",
        country_location="Singapore",
        pay_period="Monthly",
        mid_salary_sgd=1234.5,
        source="job_market_csv",
        external_id="42",
        external_apply_url="https://example.com/jobs/42",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    from app.services.job_portal_service import JobPortalService

    serialized = JobPortalService(db_session)._serialize_job(job)

    assert serialized["source_id"] == 42
    assert serialized["city_location"] == "Singapore"
    assert serialized["country_location"] == "Singapore"
    assert serialized["pay_period"] == "Monthly"
    assert serialized["mid_salary_sgd"] == 1234.5


def test_list_jobs_returns_active_jobs_without_fixed_order(client: TestClient, db_session: Session) -> None:
    db_session.add_all(
        [
            Job(
                id=uuid4(),
                job_title="Role B",
                job_description="Second",
                company_name="Beta Co",
                location="Singapore",
                source="job_market_csv",
                external_id="b",
                external_apply_url="https://example.com/jobs/b",
                is_active=True,
            ),
            Job(
                id=uuid4(),
                job_title="Role A",
                job_description="First",
                company_name="Alpha Co",
                location="Singapore",
                source="job_market_csv",
                external_id="a",
                external_apply_url="https://example.com/jobs/a",
                is_active=True,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert {item["job_title"] for item in payload["items"]} == {"Role A", "Role B"}


def test_list_jobs_supports_pagination(client: TestClient, db_session: Session) -> None:
    for index in range(3):
        db_session.add(
            Job(
                id=uuid4(),
                job_title=f"Role {index + 1}",
                job_description="Desc",
                company_name="Example Co",
                location="Singapore",
                source="job_market_csv",
                external_id=str(index + 1),
                external_apply_url=f"https://example.com/jobs/{index + 1}",
                is_active=True,
            )
        )
    db_session.commit()

    response = client.get("/api/v1/jobs?page=2&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["page"] == 2
    assert payload["pagination"]["page_size"] == 1
    assert payload["pagination"]["total"] == 3
    assert payload["pagination"]["total_pages"] == 3
    assert len(payload["items"]) == 1

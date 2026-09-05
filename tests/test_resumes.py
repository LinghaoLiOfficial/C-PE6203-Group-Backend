from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.resume import Resume


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

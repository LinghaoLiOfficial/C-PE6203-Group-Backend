"""import job market csv data into jobs"""

from __future__ import annotations

import csv
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert

revision = "20260905_0002"
down_revision = "20260831_0001"
branch_labels = None
depends_on = None

CSV_SOURCE = "job_market_csv"
CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "job_market_data.csv"


def _build_location(row: dict[str, str]) -> str | None:
    city = (row.get("city_location") or "").strip()
    country = (row.get("country_location") or "").strip()
    if city and country:
        return f"{city}, {country}"
    return city or country or None


def _load_rows() -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            source_id = (row.get("source_id") or "").strip()
            job_title = (row.get("job_title") or "").strip()
            job_description = (row.get("job_description") or "").strip()
            company_name = (row.get("company_name") or "").strip() or None
            if not source_id or not job_title or not job_description:
                continue
            payloads.append(
                {
                    "job_name": job_title,
                    "job_description": job_description,
                    "company_name": company_name,
                    "location": _build_location(row),
                    "source": CSV_SOURCE,
                    "external_id": source_id,
                    "external_apply_url": f"https://example.com/jobs/{source_id}",
                    "embedding": None,
                    "skill_tags": None,
                    "is_active": True,
                }
            )
    return payloads


def upgrade() -> None:
    jobs = sa.table(
        "jobs",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("job_name", sa.String()),
        sa.column("job_description", sa.Text()),
        sa.column("company_name", sa.String()),
        sa.column("location", sa.String()),
        sa.column("source", sa.String()),
        sa.column("external_id", sa.String()),
        sa.column("external_apply_url", sa.Text()),
        sa.column("embedding"),
        sa.column("skill_tags"),
        sa.column("is_active", sa.Boolean()),
    )
    connection = op.get_bind()
    existing = {
        tuple(row)
        for row in connection.execute(
            sa.select(jobs.c.source, jobs.c.external_id).where(jobs.c.source == CSV_SOURCE)
        )
    }
    rows = [payload for payload in _load_rows() if (payload["source"], payload["external_id"]) not in existing]
    if rows:
        connection.execute(insert(jobs), [{**row, "id": uuid4()} for row in rows])


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM jobs WHERE source = :source"), {"source": CSV_SOURCE})

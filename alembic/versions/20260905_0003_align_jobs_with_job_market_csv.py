"""align jobs table with full job market csv fields"""

from __future__ import annotations

import csv
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "20260905_0003"
down_revision = "20260905_0002"
branch_labels = None
depends_on = None

CSV_SOURCE = "job_market_csv"
CSV_PATH = Path(__file__).resolve().parents[2] / "data" / "job_market_data.csv"


def _parse_salary(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _load_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            source_id = (row.get("source_id") or "").strip()
            job_title = (row.get("job_title") or "").strip()
            job_description = (row.get("job_description") or "").strip()
            if not source_id or not job_title or not job_description:
                continue

            city = (row.get("city_location") or "").strip() or None
            country = (row.get("country_location") or "").strip() or None
            rows.append(
                {
                    "source_id": int(source_id),
                    "job_name": job_title,
                    "job_description": job_description,
                    "company_name": (row.get("company_name") or "").strip() or None,
                    "location": ", ".join(part for part in (city, country) if part) or None,
                    "city_location": city,
                    "country_location": country,
                    "pay_period": (row.get("pay_period") or "").strip() or None,
                    "mid_salary_sgd": _parse_salary(row.get("mid_salary_sgd")),
                    "external_apply_url": f"https://example.com/jobs/{source_id}",
                    "external_id": source_id,
                }
            )
    return rows


def upgrade() -> None:
    op.add_column("jobs", sa.Column("source_id", sa.Integer(), nullable=True))
    op.add_column("jobs", sa.Column("city_location", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("country_location", sa.String(255), nullable=True))
    op.add_column("jobs", sa.Column("pay_period", sa.String(50), nullable=True))
    op.add_column("jobs", sa.Column("mid_salary_sgd", sa.Float(), nullable=True))

    jobs = sa.table(
        "jobs",
        sa.column("source", sa.String()),
        sa.column("external_id", sa.String()),
        sa.column("source_id", sa.Integer()),
        sa.column("job_name", sa.String()),
        sa.column("job_description", sa.Text()),
        sa.column("company_name", sa.String()),
        sa.column("location", sa.String()),
        sa.column("city_location", sa.String()),
        sa.column("country_location", sa.String()),
        sa.column("pay_period", sa.String()),
        sa.column("mid_salary_sgd", sa.Float()),
        sa.column("external_apply_url", sa.Text()),
    )
    connection = op.get_bind()
    for row in _load_rows():
        connection.execute(
            sa.update(jobs)
            .where(jobs.c.source == CSV_SOURCE, jobs.c.external_id == row["external_id"])
            .values(
                source_id=row["source_id"],
                job_name=row["job_name"],
                job_description=row["job_description"],
                company_name=row["company_name"],
                location=row["location"],
                city_location=row["city_location"],
                country_location=row["country_location"],
                pay_period=row["pay_period"],
                mid_salary_sgd=row["mid_salary_sgd"],
                external_apply_url=row["external_apply_url"],
            )
        )


def downgrade() -> None:
    op.drop_column("jobs", "mid_salary_sgd")
    op.drop_column("jobs", "pay_period")
    op.drop_column("jobs", "country_location")
    op.drop_column("jobs", "city_location")
    op.drop_column("jobs", "source_id")

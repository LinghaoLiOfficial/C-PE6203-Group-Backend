from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job import Job
from app.models.job_import import JobImportBatch, JobImportRow
from app.services.embedding_service import embed_text
from app.services.job_portal_service import JobPortalService

CSV_FIELD_ALIASES = {
    "source_id": {"source_id"},
    "job_title": {"job_title", "title"},
    "job_description": {"job_description", "description"},
    "company_name": {"company_name", "company"},
    "mid_salary_sgd": {"mid_salary_sgd", "salary", "mid_salary"},
    "pay_period": {"pay_period"},
    "country_location": {"country_location", "country"},
    "city_location": {"city_location", "city"},
    "external_apply_url": {"external_apply_url", "apply_url", "url"},
    "external_id": {"external_id", "id"},
    "source": {"source"},
    "location": {"location"},
}


class JobImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.portal_service = JobPortalService(db)

    def preview_upload(self, admin_user_id: UUID, upload: UploadFile) -> dict[str, object]:
        rows = self._parse_csv(upload)
        batch = JobImportBatch(
            admin_user_id=admin_user_id,
            file_name=upload.filename or "jobs.csv",
            status="preview",
            total_rows=len(rows),
            source="admin_csv",
        )
        self.db.add(batch)
        self.db.flush()

        prepared_rows = []
        seen: set[str] = set()
        existing_keys = self._load_existing_keys()
        pending_insert = 0
        pending_update = 0
        duplicate_rows = 0
        error_rows = 0

        for index, raw_row in enumerate(rows, start=1):
            normalized, error = self._normalize_row(raw_row)
            dedupe_key = self._dedupe_key(normalized) if normalized else None
            canonical_profile = (
                self._build_canonical_job_profile(normalized, dedupe_key)
                if normalized and dedupe_key
                else None
            )
            if normalized and canonical_profile:
                normalized["canonical_job_profile"] = canonical_profile
            status_value = "error"
            if error:
                error_rows += 1
            elif dedupe_key in seen:
                duplicate_rows += 1
                status_value = "duplicate"
            elif dedupe_key and dedupe_key in existing_keys:
                pending_update += 1
                status_value = "pending_update"
            else:
                pending_insert += 1
                status_value = "pending_insert"
            if dedupe_key:
                seen.add(dedupe_key)
            row = JobImportRow(
                batch_id=batch.id,
                row_number=index,
                status=status_value,
                dedupe_key=dedupe_key,
                raw_payload=raw_row,
                normalized_payload=normalized,
                error_message=error,
            )
            self.db.add(row)
            prepared_rows.append(row)

        batch.pending_insert_rows = pending_insert
        batch.pending_update_rows = pending_update
        batch.duplicate_rows = duplicate_rows
        batch.error_rows = error_rows
        self.db.commit()
        self.db.refresh(batch)
        return self._serialize_batch(batch, prepared_rows)

    def confirm_import(self, admin_user_id: UUID, batch_id: UUID) -> dict[str, object]:
        batch = self._get_batch(batch_id, admin_user_id)
        rows = list(
            self.db.scalars(
                select(JobImportRow)
                .where(JobImportRow.batch_id == batch.id)
                .order_by(JobImportRow.row_number)
            )
        )
        if batch.status == "imported":
            return self._serialize_batch(batch, rows)

        for row in rows:
            if row.status not in {"pending_insert", "pending_update"} or not row.normalized_payload:
                row.status = row.status if row.status != "pending_insert" else "skipped"
                continue
            payload = row.normalized_payload
            job = self._upsert_job(payload)
            row.job_id = job.id
            row.status = "updated" if row.status == "pending_update" else "inserted"
            self._refresh_job_market_profile(job, payload)
            row.normalized_payload = payload

        batch.status = "imported"
        batch.inserted_rows = sum(1 for row in rows if row.status == "inserted")
        batch.updated_rows = sum(1 for row in rows if row.status == "updated")
        batch.skipped_rows = sum(
            1 for row in rows if row.status in {"duplicate", "error"}
        )
        batch.imported_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(batch)
        rows = list(
            self.db.scalars(
                select(JobImportRow)
                .where(JobImportRow.batch_id == batch.id)
                .order_by(JobImportRow.row_number)
            )
        )
        return self._serialize_batch(batch, rows)

    def list_history(self, admin_user_id: UUID) -> dict[str, object]:
        batches = list(
            self.db.scalars(
                select(JobImportBatch)
                .where(JobImportBatch.admin_user_id == admin_user_id)
                .order_by(JobImportBatch.created_at.desc())
            )
        )
        return {
            "items": [
                {
                    "id": batch.id,
                    "file_name": batch.file_name,
                    "status": batch.status,
                    "total_rows": batch.total_rows,
                    "inserted_rows": batch.inserted_rows,
                    "updated_rows": batch.updated_rows,
                    "skipped_rows": batch.skipped_rows,
                    "error_rows": batch.error_rows,
                    "created_at": batch.created_at,
                    "imported_at": batch.imported_at,
                }
                for batch in batches
            ]
        }

    def _parse_csv(self, upload: UploadFile) -> list[dict[str, str]]:
        data = upload.file.read()
        if len(data) > settings.max_resume_upload_bytes * 4:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File is too large.",
            )
        text = data.decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        return [
            dict(row)
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]

    def _normalize_row(self, row: dict[str, str]) -> tuple[dict[str, object] | None, str | None]:
        normalized: dict[str, object] = {}
        for canonical, aliases in CSV_FIELD_ALIASES.items():
            value = self._first_nonempty(row, aliases)
            if value is not None:
                normalized[canonical] = value
        if not normalized.get("job_title") or not normalized.get("company_name"):
            return None, "Missing job_title or company_name."
        normalized["job_title"] = self._clean_text(str(normalized["job_title"]))
        normalized["company_name"] = self._clean_text(str(normalized["company_name"]))
        normalized["city_location"] = (
            self._clean_text(str(normalized.get("city_location", ""))) or None
        )
        normalized["country_location"] = (
            self._clean_text(str(normalized.get("country_location", ""))) or None
        )
        normalized["job_description"] = str(normalized.get("job_description") or "").strip()
        normalized["source"] = str(normalized.get("source") or "admin_csv").strip() or "admin_csv"
        normalized["external_id"] = str(
            normalized.get("external_id") or self._dedupe_key(normalized)
        )
        normalized["location"] = self._compose_location(normalized) or None
        normalized["external_apply_url"] = str(
            normalized.get("external_apply_url") or ""
        ).strip()
        if not normalized["external_apply_url"]:
            normalized["external_apply_url"] = f"https://jobs.local/{normalized['external_id']}"
        source_id = normalized.get("source_id")
        if source_id not in (None, ""):
            try:
                normalized["source_id"] = int(float(str(source_id)))
            except ValueError:
                normalized["source_id"] = None
        salary = normalized.get("mid_salary_sgd")
        if salary not in (None, ""):
            try:
                normalized["mid_salary_sgd"] = float(str(salary))
            except ValueError:
                normalized["mid_salary_sgd"] = None
        return normalized, None

    def _upsert_job(self, payload: dict[str, object]) -> Job:
        key = self._dedupe_key(payload)
        existing = self._find_existing_job(self._dedupe_key(payload))
        if existing is None:
            existing = self.db.scalar(
                select(Job).where(Job.external_id == payload.get("external_id"))
            )
        if existing is None:
            existing = Job(
                job_title=str(payload.get("job_title")),
                job_description=str(payload.get("job_description") or ""),
                source_id=payload.get("source_id"),
                company_name=payload.get("company_name"),
                location=self._compose_location(payload),
                city_location=payload.get("city_location"),
                country_location=payload.get("country_location"),
                pay_period=payload.get("pay_period"),
                mid_salary_sgd=payload.get("mid_salary_sgd"),
                source=str(payload.get("source") or "admin_csv"),
                external_id=str(payload.get("external_id") or key),
                external_apply_url=str(payload.get("external_apply_url") or f"https://jobs.local/{key}"),
                embedding=embed_text(str(payload.get("job_description") or "")),
                skill_tags=self.portal_service._extract_skills(
                    str(payload.get("job_description") or "")
                ),
                is_active=True,
            )
            self.db.add(existing)
            self.db.flush()
            return existing

        existing.job_description = str(payload.get("job_description") or existing.job_description)
        existing.source_id = (
            payload.get("source_id")
            if payload.get("source_id") is not None
            else existing.source_id
        )
        existing.company_name = payload.get("company_name") or existing.company_name
        existing.location = self._compose_location(payload) or existing.location
        existing.city_location = payload.get("city_location") or existing.city_location
        existing.country_location = payload.get("country_location") or existing.country_location
        existing.pay_period = payload.get("pay_period") or existing.pay_period
        existing.mid_salary_sgd = payload.get("mid_salary_sgd") or existing.mid_salary_sgd
        existing.source = str(payload.get("source") or existing.source)
        existing.external_id = str(payload.get("external_id") or existing.external_id)
        existing.external_apply_url = str(
            payload.get("external_apply_url") or existing.external_apply_url
        )
        existing.embedding = embed_text(existing.job_description)
        existing.skill_tags = self.portal_service._extract_skills(existing.job_description)
        existing.is_active = True
        self.db.add(existing)
        self.db.flush()
        return existing

    def _refresh_job_market_profile(self, job: Job, payload: dict[str, object]) -> None:
        profile = payload.get("canonical_job_profile")
        if isinstance(profile, dict):
            self.portal_service._upsert_job_market_profile_payload(job, profile)
        else:
            self.portal_service._upsert_job_market_profile(job)

    def _load_existing_keys(self) -> set[str]:
        jobs = self.db.scalars(select(Job)).all()
        return {
            self._dedupe_key(
                {
                    "company_name": job.company_name,
                    "city_location": job.city_location,
                    "country_location": job.country_location,
                    "job_title": job.job_title,
                }
            )
            for job in jobs
        }

    def _get_batch(self, batch_id: UUID, admin_user_id: UUID) -> JobImportBatch:
        batch = self.db.scalar(
            select(JobImportBatch).where(
                JobImportBatch.id == batch_id,
                JobImportBatch.admin_user_id == admin_user_id,
            )
        )
        if batch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Import batch not found.",
            )
        return batch

    def _serialize_batch(
        self, batch: JobImportBatch, rows: list[JobImportRow]
    ) -> dict[str, object]:
        return {
            "batch": {
                "id": batch.id,
                "admin_user_id": batch.admin_user_id,
                "file_name": batch.file_name,
                "status": batch.status,
                "total_rows": batch.total_rows,
                "pending_insert_rows": batch.pending_insert_rows,
                "pending_update_rows": batch.pending_update_rows,
                "duplicate_rows": batch.duplicate_rows,
                "error_rows": batch.error_rows,
                "inserted_rows": batch.inserted_rows,
                "updated_rows": batch.updated_rows,
                "skipped_rows": batch.skipped_rows,
                "source": batch.source,
                "created_at": batch.created_at,
                "imported_at": batch.imported_at,
                "rows": [
                    {
                        "row_number": row.row_number,
                        "status": row.status,
                        "dedupe_key": row.dedupe_key,
                        "error_message": row.error_message,
                        "raw_payload": row.raw_payload,
                        "normalized_payload": row.normalized_payload,
                        "canonical_job_profile": (
                            row.normalized_payload.get("canonical_job_profile")
                            if row.normalized_payload
                            else None
                        ),
                        "job_id": row.job_id,
                    }
                    for row in rows
                ],
            }
        }

    def _build_canonical_job_profile(
        self, payload: dict[str, object], dedupe_key: str
    ) -> dict[str, object]:
        profile = self.portal_service._extract_job_requirements(
            str(payload.get("job_title") or ""),
            str(payload.get("job_description") or ""),
        )
        profile["canonical_key"] = dedupe_key
        profile["source_provenance"] = {
            "source": payload.get("source") or "admin_csv",
            "external_id": payload.get("external_id") or dedupe_key,
            "external_apply_url": payload.get("external_apply_url"),
        }
        profile["location"] = {
            "city": payload.get("city_location"),
            "country": payload.get("country_location"),
            "display": payload.get("location"),
        }
        profile["salary"] = {
            "mid_salary_sgd": payload.get("mid_salary_sgd"),
            "pay_period": payload.get("pay_period"),
            "confidence": profile.get("salary_confidence", "C"),
        }
        profile["normalized_dimensions"] = {
            "skills": sorted(
                set(profile.get("required_skills") or [])
                | set(profile.get("preferred_skills") or [])
            ),
            "seniority": profile.get("seniority"),
            "occupation_family": profile.get("occupation_family"),
            "location": payload.get("location"),
        }
        return profile

    def _first_nonempty(self, row: dict[str, str], aliases: set[str]) -> str | None:
        for key, value in row.items():
            if key.strip().lower() in aliases and value and str(value).strip():
                return str(value).strip()
        return None

    def _clean_text(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value)
        normalized = normalized.replace("\u00a0", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _dedupe_key(self, payload: dict[str, object]) -> str:
        parts = [
            self._key_text(str(payload.get("company_name") or "")),
            self._key_text(str(payload.get("city_location") or "")),
            self._key_text(str(payload.get("country_location") or "")),
            self._key_text(str(payload.get("job_title") or "")),
        ]
        return "|".join(parts)

    def _key_text(self, value: str) -> str:
        return self._clean_text(value).lower()

    def _find_existing_job(self, dedupe_key: str) -> Job | None:
        for job in self.db.scalars(select(Job)):
            if self._dedupe_key(
                {
                    "company_name": job.company_name,
                    "city_location": job.city_location,
                    "country_location": job.country_location,
                    "job_title": job.job_title,
                }
            ) == dedupe_key:
                return job
        return None

    def _compose_location(self, payload: dict[str, object]) -> str | None:
        city = str(payload.get("city_location") or "").strip()
        country = str(payload.get("country_location") or "").strip()
        if city and country:
            return f"{city}, {country}"
        return city or country or None

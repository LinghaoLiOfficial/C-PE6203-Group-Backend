from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base_class import Base


class JobImportBatch(Base):
    __tablename__ = "job_import_batches"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    admin_user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="preview")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_insert_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_update_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="admin_csv")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(UTC)
    )
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobImportRow(Base):
    __tablename__ = "job_import_rows"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("job_import_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending_insert")
    dedupe_key: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    normalized_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(UTC)
    )

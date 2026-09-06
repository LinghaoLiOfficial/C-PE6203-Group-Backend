"""add job import tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260905_0007"
down_revision = "20260905_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    jsonb = postgresql.JSONB()

    op.create_table(
        "job_import_batches",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("admin_user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="preview"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_insert_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_update_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(50), nullable=False, server_default="admin_csv"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "job_import_rows",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("batch_id", uuid, sa.ForeignKey("job_import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_insert"),
        sa.Column("dedupe_key", sa.Text(), nullable=True),
        sa.Column("raw_payload", jsonb, nullable=True),
        sa.Column("normalized_payload", jsonb, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_import_batches_admin_user_id", "job_import_batches", ["admin_user_id"])
    op.create_index("ix_job_import_rows_batch_id", "job_import_rows", ["batch_id"])
    op.create_index("ix_job_import_rows_dedupe_key", "job_import_rows", ["dedupe_key"])
    op.create_index("ix_job_import_rows_job_id", "job_import_rows", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_job_import_rows_job_id", table_name="job_import_rows")
    op.drop_index("ix_job_import_rows_dedupe_key", table_name="job_import_rows")
    op.drop_index("ix_job_import_rows_batch_id", table_name="job_import_rows")
    op.drop_index("ix_job_import_batches_admin_user_id", table_name="job_import_batches")
    op.drop_table("job_import_rows")
    op.drop_table("job_import_batches")

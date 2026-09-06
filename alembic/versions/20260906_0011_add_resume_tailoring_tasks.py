"""add asynchronous tailored resume tasks and structured output"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260906_0011"
down_revision = "20260906_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "resume_tailoring_tasks",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", uuid, sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("worker_id", sa.String(100)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for name in ("user_id", "resume_id", "job_id", "status"):
        op.create_index(f"ix_resume_tailoring_tasks_{name}", "resume_tailoring_tasks", [name])
    for name in ("resume_sections", "change_summary", "evidence_used", "target_requirements"):
        op.add_column("resume_variants", sa.Column(name, postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    for name in ("target_requirements", "evidence_used", "change_summary", "resume_sections"):
        op.drop_column("resume_variants", name)
    for name in ("status", "job_id", "resume_id", "user_id"):
        op.drop_index(f"ix_resume_tailoring_tasks_{name}", table_name="resume_tailoring_tasks")
    op.drop_table("resume_tailoring_tasks")

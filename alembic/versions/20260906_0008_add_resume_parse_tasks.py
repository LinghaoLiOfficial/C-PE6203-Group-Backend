"""add persisted resume parse tasks"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260906_0008"
down_revision = "20260905_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "resume_parse_tasks",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("resume_id", uuid, sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("worker_id", sa.String(100)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resume_parse_tasks_resume_id", "resume_parse_tasks", ["resume_id"])
    op.create_index("ix_resume_parse_tasks_user_id", "resume_parse_tasks", ["user_id"])
    op.create_index("ix_resume_parse_tasks_status", "resume_parse_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_resume_parse_tasks_status", table_name="resume_parse_tasks")
    op.drop_index("ix_resume_parse_tasks_user_id", table_name="resume_parse_tasks")
    op.drop_index("ix_resume_parse_tasks_resume_id", table_name="resume_parse_tasks")
    op.drop_table("resume_parse_tasks")

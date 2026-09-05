"""add job_title to jobs"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260905_0004"
down_revision = "20260905_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("job_title", sa.String(500), nullable=True))
    op.execute(sa.text("UPDATE jobs SET job_title = job_name WHERE job_title IS NULL"))


def downgrade() -> None:
    op.drop_column("jobs", "job_title")

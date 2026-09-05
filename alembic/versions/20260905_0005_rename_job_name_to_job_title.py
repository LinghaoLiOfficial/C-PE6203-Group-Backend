"""drop legacy job_name after job_title backfill"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260905_0005"
down_revision = "20260905_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("jobs", "job_name")


def downgrade() -> None:
    op.add_column("jobs", sa.Column("job_name", sa.String(500), nullable=True))
    op.execute(sa.text("UPDATE jobs SET job_name = job_title WHERE job_name IS NULL"))

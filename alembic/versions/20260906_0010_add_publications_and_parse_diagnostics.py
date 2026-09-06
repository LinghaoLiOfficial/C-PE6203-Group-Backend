"""add publications to candidate graphs and diagnostics to parse tasks"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260906_0010"
down_revision = "20260906_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    jsonb = postgresql.JSONB()
    op.add_column("candidate_graphs", sa.Column("publications", jsonb))
    op.add_column("resume_parse_tasks", sa.Column("diagnostics", jsonb))


def downgrade() -> None:
    op.drop_column("resume_parse_tasks", "diagnostics")
    op.drop_column("candidate_graphs", "publications")

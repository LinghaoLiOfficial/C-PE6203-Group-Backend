"""add experience highlights to candidate graphs"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260906_0009"
down_revision = "20260906_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    jsonb = postgresql.JSONB()
    op.add_column("candidate_graphs", sa.Column("experience_highlights", jsonb))


def downgrade() -> None:
    op.drop_column("candidate_graphs", "experience_highlights")

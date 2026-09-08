"""add experience highlights to candidate graphs"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "20260906_0009"
down_revision = "20260906_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0006 already creates `experience_highlights` in `candidate_graphs`, so this
    # migration is redundant on a fresh database. Guard against the duplicate
    # column so `alembic upgrade head` works on both fresh and already-migrated DBs.
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("candidate_graphs")}
    if "experience_highlights" not in existing:
        jsonb = postgresql.JSONB()
        op.add_column("candidate_graphs", sa.Column("experience_highlights", jsonb))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("candidate_graphs")}
    if "experience_highlights" in existing:
        op.drop_column("candidate_graphs", "experience_highlights")

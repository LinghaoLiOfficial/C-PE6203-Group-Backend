"""add career opportunity model"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260905_0006"
down_revision = "20260905_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    jsonb = postgresql.JSONB()
    op.create_table(
        "candidate_graphs",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", uuid, sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("skills", jsonb),
        sa.Column("experience_highlights", jsonb),
        sa.Column("experiences", jsonb),
        sa.Column("education", jsonb),
        sa.Column("projects", jsonb),
        sa.Column("achievements", jsonb),
        sa.Column("constraints", jsonb),
        sa.Column("preferences", jsonb),
        sa.Column("source_spans", jsonb),
        sa.Column("user_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_candidate_graphs_user_id", "candidate_graphs", ["user_id"])
    op.create_index("ix_candidate_graphs_resume_id", "candidate_graphs", ["resume_id"])

    op.create_table(
        "job_market_profiles",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("occupation_family", sa.String(120)),
        sa.Column("seniority", sa.String(80)),
        sa.Column("required_skills", jsonb),
        sa.Column("preferred_skills", jsonb),
        sa.Column("education_requirements", jsonb),
        sa.Column("experience_requirements", jsonb),
        sa.Column("licenses", jsonb),
        sa.Column("salary_confidence", sa.String(20), nullable=False, server_default="C"),
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("raw_requirements", jsonb),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("job_id", name="uq_job_market_profiles_job_id"),
    )
    op.create_index("ix_job_market_profiles_job_id", "job_market_profiles", ["job_id"])

    op.create_table(
        "candidate_job_matches",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", uuid, sa.ForeignKey("resumes.id", ondelete="SET NULL")),
        sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("category", sa.String(40), nullable=False, server_default="stretch"),
        sa.Column("score_vector", jsonb),
        sa.Column("fit_breakdown", jsonb),
        sa.Column("rationale", jsonb),
        sa.Column("transition_difficulty", sa.String(40), nullable=False, server_default="moderate"),
        sa.Column("data_confidence", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "job_id", name="uq_candidate_job_matches_user_job"),
    )
    op.create_index("ix_candidate_job_matches_user_id", "candidate_job_matches", ["user_id"])
    op.create_index("ix_candidate_job_matches_resume_id", "candidate_job_matches", ["resume_id"])
    op.create_index("ix_candidate_job_matches_job_id", "candidate_job_matches", ["job_id"])

    op.create_table(
        "feedback_events",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="SET NULL")),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("payload", jsonb),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_feedback_events_user_id", "feedback_events", ["user_id"])
    op.create_index("ix_feedback_events_job_id", "feedback_events", ["job_id"])

    op.create_table(
        "resume_variants",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", uuid, sa.ForeignKey("resumes.id", ondelete="SET NULL")),
        sa.Column("job_id", uuid, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan", jsonb),
        sa.Column("claims", jsonb),
        sa.Column("validation_results", jsonb),
        sa.Column("rewritten_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resume_variants_user_id", "resume_variants", ["user_id"])
    op.create_index("ix_resume_variants_resume_id", "resume_variants", ["resume_id"])
    op.create_index("ix_resume_variants_job_id", "resume_variants", ["job_id"])


def downgrade() -> None:
    op.drop_table("resume_variants")
    op.drop_table("feedback_events")
    op.drop_table("candidate_job_matches")
    op.drop_table("job_market_profiles")
    op.drop_table("candidate_graphs")

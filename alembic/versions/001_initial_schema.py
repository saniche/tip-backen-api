"""Create the initial Talent Intelligence Platform schema."""

from alembic import op
import sqlalchemy as sa


revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
    )
    op.create_table(
        "profile_sessions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.Enum("CREATED", "PROCESSING", "COMPLETED", "FAILED", name="profilesessionstatus"), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("url", sa.String(), unique=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("company", sa.String()),
        sa.Column("location", sa.String()),
        sa.Column("salary", sa.String()),
        sa.Column("source", sa.String()),
        sa.Column("summary", sa.Text()),
        sa.Column("posting_date", sa.String()),
        sa.Column("key_responsibilities", sa.JSON()),
        sa.Column("required", sa.JSON()),
        sa.Column("desirable", sa.JSON()),
        sa.Column("technical_stack", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("submitter_id", sa.String(), sa.ForeignKey("users.id")),
    )
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON()),
        sa.Column("output_language", sa.String(), nullable=False, server_default="English"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "user_files",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.String(), sa.ForeignKey("profile_sessions.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="profilefilestatus"), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "profile_fragments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("file_id", sa.String(), sa.ForeignKey("user_files.id"), nullable=False),
        sa.Column("data", sa.JSON()),
        sa.Column("evidence_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "job_interests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "job_id", name="uq_job_interest_user_job"),
    )
    op.create_table(
        "match_reports",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("user_profiles.id")),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("rules_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "job_matchings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("report_id", sa.String(), sa.ForeignKey("match_reports.id")),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("user_profiles.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column("scoring_status", sa.String(), nullable=False),
        sa.Column("breakdown", sa.JSON()),
        sa.Column("llm_match_output", sa.JSON(), nullable=False),
        sa.Column("profile_snapshot", sa.JSON()),
        sa.Column("job_snapshot", sa.JSON()),
        sa.Column("rules_version", sa.String(), nullable=False, server_default="v1"),
        sa.Column("rank", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "tailored_cvs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("matching_id", sa.String(), sa.ForeignKey("job_matchings.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("blob_path", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_type", sa.Enum("PROFILE_BUILD", "CV_TAILOR", name="processingjobtype"), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "RUNNING", "DONE", "FAILED", name="processingjobstatus"), nullable=False),
        sa.Column("result_id", sa.String()),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for table in ("processing_jobs", "tailored_cvs", "job_matchings", "match_reports", "job_interests", "profile_fragments", "user_files", "user_profiles", "jobs", "profile_sessions", "users"):
        op.drop_table(table)
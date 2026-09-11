"""Add jobs and interests query indexes."""

from alembic import op

revision = "002_jobs_and_interests"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    op.create_index("ix_jobs_submitter_id", "jobs", ["submitter_id"])
    op.create_index("ix_job_interests_user_job", "job_interests", ["user_id", "job_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_job_interests_user_job", table_name="job_interests")
    op.drop_index("ix_jobs_submitter_id", table_name="jobs")
    op.drop_index("ix_jobs_created_at", table_name="jobs")

"""Add index supporting the owner-scoped, newest-first interest listing."""

from alembic import op

revision = "008_interest_listing_index"
down_revision = "007_job_additionals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_job_interests_user_created", "job_interests", ["user_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_job_interests_user_created", table_name="job_interests")

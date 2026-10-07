"""Add output language to profile build sessions."""

import sqlalchemy as sa

from alembic import op

revision = "006_profile_language"
down_revision = "005_matching_processing_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "profile_sessions",
        sa.Column("output_language", sa.String(), nullable=False, server_default="English"),
    )


def downgrade() -> None:
    op.drop_column("profile_sessions", "output_language")

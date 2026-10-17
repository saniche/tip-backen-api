"""Add additional normalized job information."""

import sqlalchemy as sa

from alembic import op

revision = "007_job_additionals"
down_revision = "006_profile_language"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("additionals", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("jobs", "additionals")

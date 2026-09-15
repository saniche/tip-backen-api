"""Add matching as a processing job type."""

from alembic import op

revision = "005_matching_processing_jobs"
down_revision = "004_tailored_cvs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE processingjobtype ADD VALUE IF NOT EXISTS 'MATCHING'")


def downgrade() -> None:
    pass
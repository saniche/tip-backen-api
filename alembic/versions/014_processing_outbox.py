"""Persist background work until the queue and worker have completed it."""

import sqlalchemy as sa

from alembic import op

revision = "014_processing_outbox"
down_revision = "013_tailoring_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])
    op.create_table(
        "processing_outbox",
        sa.Column(
            "processing_job_id",
            sa.String(),
            sa.ForeignKey("processing_jobs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("task_name", sa.String(), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("processing_outbox")
    op.drop_index("ix_processing_jobs_status", table_name="processing_jobs")

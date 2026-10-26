"""Allow unscorable matching results to store a null score."""

import sqlalchemy as sa

from alembic import op

revision = "010_matching_nullable_score"
down_revision = "009_application_journal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("job_matchings") as batch_op:
        batch_op.alter_column(
            "score",
            existing_type=sa.Float(),
            nullable=True,
        )


def downgrade() -> None:
    null_scores = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM job_matchings WHERE score IS NULL")
    ).scalar_one()
    if null_scores:
        raise RuntimeError("Cannot make job_matchings.score non-nullable while null scores exist.")
    with op.batch_alter_table("job_matchings") as batch_op:
        batch_op.alter_column(
            "score",
            existing_type=sa.Float(),
            nullable=False,
        )

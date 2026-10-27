"""Rename the normalized job tools and technologies column."""

import sqlalchemy as sa

from alembic import op

revision = "011_tools_and_technologies"
down_revision = "010_matching_nullable_score"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column(
            "technical_stack",
            new_column_name="tools_and_technologies",
            existing_type=sa.JSON(),
        )


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.alter_column(
            "tools_and_technologies",
            new_column_name="technical_stack",
            existing_type=sa.JSON(),
        )

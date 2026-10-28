"""Multiple profiles per user: label, updated_at and soft delete on user_profiles."""

import sqlalchemy as sa

from alembic import op

revision = "012_profile_management"
down_revision = "011_tools_and_technologies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(sa.Column("label", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("label")

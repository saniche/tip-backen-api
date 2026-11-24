"""Move identity to Keycloak: users becomes a local mirror of the Keycloak identity.

Drops the locally stored password hash and adds the Keycloak subject plus profile columns that are
synced from the access token. Existing rows keep their id (and therefore all foreign keys) and are
linked to Keycloak by verified email on the user's first Keycloak login.
"""

import sqlalchemy as sa

from alembic import op

revision = "015_keycloak_users"
down_revision = "014_processing_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("keycloak_sub", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("username", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("first_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_name", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_users_keycloak_sub", ["keycloak_sub"], unique=True)
        batch_op.drop_column("hashed_password")


def downgrade() -> None:
    # Password hashes cannot be restored; legacy rows come back with a NULL hash.
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("hashed_password", sa.String(), nullable=True))
        batch_op.drop_index("ix_users_keycloak_sub")
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("last_name")
        batch_op.drop_column("first_name")
        batch_op.drop_column("username")
        batch_op.drop_column("email_verified")
        batch_op.drop_column("keycloak_sub")

"""Record the matching report snapshot contract."""

from alembic import op


revision = "003_matching_reports"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The initial baseline already contains the report snapshot columns. This
    # revision reserves the explicit matching phase migration in the chain.
    pass


def downgrade() -> None:
    pass
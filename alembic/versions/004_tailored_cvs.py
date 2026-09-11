"""Record the tailored CV request and metadata contract."""

import sqlalchemy as sa

from alembic import op

revision = "004_tailored_cvs"
down_revision = "003_matching_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cv_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("matching_ids", sa.JSON()),
        sa.Column("mode", sa.String(), nullable=False, server_default="per_job"),
        sa.Column("status", sa.String(), nullable=False, server_default="completed"),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    with op.batch_alter_table("tailored_cvs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "request_id",
                sa.String(),
                sa.ForeignKey("cv_requests.id", name="fk_tailored_cvs_request_id"),
                nullable=True,
            )
        )
    op.add_column("tailored_cvs", sa.Column("mode", sa.String(), nullable=True, server_default="per_job"))
    op.add_column("tailored_cvs", sa.Column("status", sa.String(), nullable=True, server_default="completed"))
    op.add_column("tailored_cvs", sa.Column("target_job_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tailored_cvs") as batch_op:
        batch_op.drop_column("request_id")
    op.drop_table("cv_requests")
    op.drop_column("tailored_cvs", "target_job_ids")
    op.drop_column("tailored_cvs", "status")
    op.drop_column("tailored_cvs", "mode")
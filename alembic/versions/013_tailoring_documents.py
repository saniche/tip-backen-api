"""Tailoring v2: default documents, cover letters, job_id based requests, partial-failure fields."""

import sqlalchemy as sa

from alembic import op

revision = "013_tailoring_documents"
down_revision = "012_profile_management"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "kind", name="uq_user_document_user_kind"),
    )

    with op.batch_alter_table("cv_requests") as batch_op:
        batch_op.add_column(sa.Column("job_ids", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("profile_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("cover_letter_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("cover_letter_mode", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("output_language", sa.String(), nullable=False, server_default="English"))
        batch_op.create_foreign_key("fk_cv_requests_profile_id", "user_profiles", ["profile_id"], ["id"])

    with op.batch_alter_table("tailored_cvs") as batch_op:
        batch_op.alter_column("matching_id", existing_type=sa.String(), nullable=True)
        batch_op.add_column(sa.Column("kind", sa.String(), nullable=False, server_default="cv"))
        batch_op.add_column(sa.Column("job_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("profile_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("warning", sa.Text(), nullable=True))
        batch_op.create_foreign_key("fk_tailored_cvs_job_id", "jobs", ["job_id"], ["id"])
        batch_op.create_foreign_key("fk_tailored_cvs_profile_id", "user_profiles", ["profile_id"], ["id"])


def downgrade() -> None:
    # Cover letters and job_id based rows have no legacy representation: drop them first.
    op.execute("DELETE FROM tailored_cvs WHERE kind <> 'cv' OR matching_id IS NULL")
    with op.batch_alter_table("tailored_cvs") as batch_op:
        batch_op.drop_constraint("fk_tailored_cvs_profile_id", type_="foreignkey")
        batch_op.drop_constraint("fk_tailored_cvs_job_id", type_="foreignkey")
        batch_op.drop_column("warning")
        batch_op.drop_column("error")
        batch_op.drop_column("profile_id")
        batch_op.drop_column("job_id")
        batch_op.drop_column("kind")
        batch_op.alter_column("matching_id", existing_type=sa.String(), nullable=False)

    with op.batch_alter_table("cv_requests") as batch_op:
        batch_op.drop_constraint("fk_cv_requests_profile_id", type_="foreignkey")
        batch_op.drop_column("output_language")
        batch_op.drop_column("cover_letter_mode")
        batch_op.drop_column("cover_letter_enabled")
        batch_op.drop_column("profile_id")
        batch_op.drop_column("job_ids")

    op.drop_table("user_documents")

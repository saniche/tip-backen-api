"""Add application journals and append-only status history."""

import sqlalchemy as sa

from alembic import op

revision = "009_application_journal"
down_revision = "008_interest_listing_index"
branch_labels = None
depends_on = None

APPLICATION_STATUSES = (
    "NotStarted",
    "Registered",
    "Applied",
    "Contacted",
    "Screening",
    "Interview",
    "OnHold",
    "Closed",
    "Rejected",
    "Offered",
    "Accepted"
)


def _status_type(name: str) -> sa.Enum:
    return sa.Enum(
        *APPLICATION_STATUSES,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
    )


def upgrade() -> None:
    op.create_table(
        "application_journals",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("recruiter_info", sa.JSON()),
        sa.Column("contact_date", sa.Date()),
        sa.Column("follow_up_date", sa.Date()),
        sa.Column("work_authorization_discussed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", _status_type("applicationstatus"), nullable=False, server_default="NotStarted"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "job_id", name="uq_application_journal_user_job"),
    )
    op.create_index(
        "ix_application_journals_user_created",
        "application_journals",
        ["user_id", "created_at", "id"],
    )

    op.create_table(
        "application_status_history",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "application_id",
            sa.String(),
            sa.ForeignKey("application_journals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("note", sa.Text()),
        sa.Column("status", _status_type("applicationstatus"), nullable=False),
    )
    op.create_index(
        "ix_application_status_history_entry_date",
        "application_status_history",
        ["application_id", "date", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_application_status_history_entry_date", table_name="application_status_history")
    op.drop_table("application_status_history")
    op.drop_index("ix_application_journals_user_created", table_name="application_journals")
    op.drop_table("application_journals")

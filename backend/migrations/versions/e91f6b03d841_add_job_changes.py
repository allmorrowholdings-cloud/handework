"""Add persisted job price changes."""
from alembic import op
import sqlalchemy as sa

revision = "e91f6b03d841"
down_revision = "d7f1a9c2b430"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "job_changes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("booking_id", sa.String(36), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("extra_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("base_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_changes_booking_id", "job_changes", ["booking_id"])


def downgrade():
    op.drop_table("job_changes")

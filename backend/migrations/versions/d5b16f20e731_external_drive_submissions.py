"""Add reviewed external Drive submissions independently of private file assets."""
from alembic import op
import sqlalchemy as sa

revision = "d5b16f20e731"
down_revision = "ca72e0fa93bd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("drive_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id")),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("drive_id", sa.String(256), nullable=False),
        sa.Column("item_kind", sa.String(12), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_note", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    for column in ("owner_id", "course_id", "status", "created_at"):
        op.create_index(f"ix_drive_submissions_{column}", "drive_submissions", [column])


def downgrade():
    op.drop_table("drive_submissions")

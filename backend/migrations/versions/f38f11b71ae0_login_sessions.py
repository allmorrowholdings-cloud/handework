"""Track idle and signed-out browser sessions."""
from alembic import op
import sqlalchemy as sa

revision = "f38f11b71ae0"
down_revision = "e91f6b03d841"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("login_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table("login_sessions")

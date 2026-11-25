"""Durable email delivery scheduling, recipient budget and session revocation."""
from alembic import op
import sqlalchemy as sa

revision = "ca72e0fa93bd"
down_revision = "a8e4c17b6321"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("notifications", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("notifications", sa.Column("next_attempt", sa.DateTime(timezone=True)))
    table = op.create_table("email_quota", sa.Column("id", sa.Integer(), primary_key=True),
                            sa.Column("window_start", sa.DateTime(timezone=True)),
                            sa.Column("reserved", sa.Integer(), nullable=False),
                            sa.Column("blocked_until", sa.DateTime(timezone=True)))
    op.bulk_insert(table, [{"id": 1, "reserved": 0}])


def downgrade():
    op.drop_table("email_quota")
    with op.batch_alter_table("notifications") as batch:
        batch.drop_column("attempts")
        batch.drop_column("next_attempt")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("session_version")

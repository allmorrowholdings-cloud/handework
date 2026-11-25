"""Add encrypted authenticator enrollment and recovery codes."""

from alembic import op
import sqlalchemy as sa


revision = "e6c27f91a842"
down_revision = "d5b16f20e731"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_totp",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True
        ),
        sa.Column("secret_encrypted", sa.String(512)),
        sa.Column("pending_secret_encrypted", sa.String(512)),
        sa.Column("pending_expires_at", sa.DateTime(timezone=True)),
        sa.Column("enabled_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_step", sa.BigInteger()),
        sa.Column("failed_attempts", sa.Integer(),
                  nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  nullable=False)
    )

    op.create_table(
        "user_totp_recovery_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("user_totp.user_id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False)
    )

    op.create_index(
        "ix_user_totp_recovery_codes_user_id",
        "user_totp_recovery_codes",
        ["user_id"]
    )


def downgrade():
    op.drop_table("user_totp_recovery_codes")
    op.drop_table("user_totp")

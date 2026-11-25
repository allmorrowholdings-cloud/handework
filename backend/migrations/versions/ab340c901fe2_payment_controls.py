"""Add payment controls without rewriting historical records."""
from alembic import op
import sqlalchemy as sa

revision = "ab340c901fe2"
down_revision = "f38f11b71ae0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("provider_disputes",
        sa.Column("provider_id", sa.String(64), primary_key=True),
        sa.Column("reference", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("resolution", sa.String(64)),
        sa.Column("deduction_units", sa.BigInteger(), nullable=False))
    op.create_index("ix_provider_disputes_reference", "provider_disputes", ["reference"])
    op.create_table("payment_jobs",
        sa.Column("cursor", sa.JSON()),
        sa.Column("key", sa.String(90), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("record_id", sa.String(36), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("last_error", sa.String(100)))
    op.create_index("ix_payment_jobs_due_at", "payment_jobs", ["due_at"])
    op.add_column("shop_orders", sa.Column("platform_fee", sa.Numeric(12,2), nullable=True))
    op.add_column("quotes", sa.Column("payment_schedule", sa.JSON(), nullable=True))
    op.create_table("journal_postings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reference", sa.String(120), nullable=False),
        sa.Column("event", sa.String(48), nullable=False),
        sa.Column("debit", sa.String(64), nullable=False),
        sa.Column("credit", sa.String(64), nullable=False),
        sa.Column("units", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("reference", "event", name="uq_journal_reference_event"))
    op.create_table("payment_controls",
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id"), primary_key=True),
        sa.Column("booking_claim", sa.String(36), unique=True),
        sa.Column("refunded", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("auto_hours", sa.Integer()),
        sa.Column("terms_version", sa.String(100)),
        sa.Column("settlement_id", sa.String(64)),
        sa.Column("provider_hold", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.create_table("payment_receipts", sa.Column("digest", sa.String(64), primary_key=True),
        sa.Column("event", sa.String(64)), sa.Column("reference", sa.String(120)), sa.Column("received_at", sa.DateTime()))
    op.create_table("payout_recipients",
        sa.Column("artisan_id", sa.String(36), sa.ForeignKey("artisan_profiles.id"), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("last_four", sa.String(4), nullable=False))
    op.create_table("payment_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("payment_id", sa.String(36), sa.ForeignKey("payments.id")),
        sa.Column("shop_order_id", sa.String(36), sa.ForeignKey("shop_orders.id")),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("request_key", sa.String(100), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("recipient", sa.String(100)),
        sa.Column("provider_id", sa.String(100)),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("kind", "provider_id", name="uq_operation_provider_id"))
    op.create_index("ix_payment_operations_shop_order_id", "payment_operations", ["shop_order_id"])
    op.create_index("ix_operation_payment", "payment_operations", ["payment_id"])


def downgrade():
    raise RuntimeError("Financial history must be retained. Roll back application code instead.")

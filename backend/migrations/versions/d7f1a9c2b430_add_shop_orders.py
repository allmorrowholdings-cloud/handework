"""add shop orders

Revision ID: d7f1a9c2b430
Revises: c4e8a621d9f0
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa

revision = "d7f1a9c2b430"
down_revision = "c4e8a621d9f0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "shop_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference", sa.String(length=32), nullable=False),
        sa.Column("buyer_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("delivery_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("fulfilment", sa.String(length=16), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("area", sa.String(length=140), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("pickup_note", sa.String(length=500), nullable=True),
        sa.Column("provider_reference", sa.String(length=120), nullable=True),
        sa.Column("provider_payload", sa.JSON(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_reference"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index(op.f("ix_shop_orders_buyer_id"), "shop_orders", ["buyer_id"], unique=False)
    op.create_index(op.f("ix_shop_orders_created_at"), "shop_orders", ["created_at"], unique=False)
    op.create_index(op.f("ix_shop_orders_provider_reference"), "shop_orders", ["provider_reference"], unique=True)
    op.create_index(op.f("ix_shop_orders_reference"), "shop_orders", ["reference"], unique=True)
    op.create_index(op.f("ix_shop_orders_status"), "shop_orders", ["status"], unique=False)

    op.create_table(
        "shop_order_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=80), nullable=False),
        sa.Column("product_name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["shop_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shop_order_items_order_id"), "shop_order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_shop_order_items_product_id"), "shop_order_items", ["product_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_shop_order_items_product_id"), table_name="shop_order_items")
    op.drop_index(op.f("ix_shop_order_items_order_id"), table_name="shop_order_items")
    op.drop_table("shop_order_items")
    op.drop_index(op.f("ix_shop_orders_status"), table_name="shop_orders")
    op.drop_index(op.f("ix_shop_orders_reference"), table_name="shop_orders")
    op.drop_index(op.f("ix_shop_orders_provider_reference"), table_name="shop_orders")
    op.drop_index(op.f("ix_shop_orders_created_at"), table_name="shop_orders")
    op.drop_index(op.f("ix_shop_orders_buyer_id"), table_name="shop_orders")
    op.drop_table("shop_orders")

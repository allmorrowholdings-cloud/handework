"""Persist object-store metadata and attach file assets to marketplace records.

Revision ID: a8e4c17b6321
Revises: ab340c901fe2
"""
from alembic import op
import sqlalchemy as sa

revision = "a8e4c17b6321"
down_revision = "ab340c901fe2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("file_assets") as batch:
        batch.add_column(sa.Column("storage_bucket", sa.String(128)))
        batch.add_column(sa.Column("storage_key", sa.String(1024)))
        batch.add_column(sa.Column("original_filename", sa.String(255)))
        batch.add_column(sa.Column("size_bytes", sa.BigInteger()))
        batch.add_column(sa.Column("sha256", sa.String(64)))
        batch.add_column(sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("replaces_asset_id", sa.String(36)))
        batch.create_foreign_key("fk_file_assets_replaces_asset_id", "file_assets", ["replaces_asset_id"], ["id"], ondelete="SET NULL")

    for table in ("portfolio_items", "verifications", "workproof_evidence"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("file_asset_id", sa.String(36)))
            batch.create_foreign_key(f"fk_{table}_file_asset_id", "file_assets", ["file_asset_id"], ["id"], ondelete="SET NULL")
            batch.create_index(f"ix_{table}_file_asset_id", ["file_asset_id"])

    with op.batch_alter_table("artisan_profiles") as batch:
        batch.add_column(sa.Column("avatar_file_id", sa.String(36)))
        batch.create_foreign_key("fk_artisan_profiles_avatar_file_id", "file_assets", ["avatar_file_id"], ["id"], ondelete="SET NULL")
    op.create_table(
        "shop_product_media",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("product_id", sa.String(80), nullable=False),
        sa.Column("file_asset_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["file_asset_id"], ["file_assets.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("product_id", name="uq_shop_product_media_product_id"),
    )
    op.create_index("ix_shop_product_media_product_id", "shop_product_media", ["product_id"])


def downgrade():
    op.drop_table("shop_product_media")
    with op.batch_alter_table("artisan_profiles") as batch:
        batch.drop_constraint("fk_artisan_profiles_avatar_file_id", type_="foreignkey")
        batch.drop_column("avatar_file_id")
    for table in ("workproof_evidence", "verifications", "portfolio_items"):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_file_asset_id")
            batch.drop_constraint(f"fk_{table}_file_asset_id", type_="foreignkey")
            batch.drop_column("file_asset_id")
    with op.batch_alter_table("file_assets") as batch:
        batch.drop_constraint("fk_file_assets_replaces_asset_id", type_="foreignkey")
        for column in ("replaces_asset_id", "deleted_at", "is_private", "sha256", "size_bytes", "original_filename", "storage_key", "storage_bucket"):
            batch.drop_column(column)

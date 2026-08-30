"""add banner and support configuration tables

Revision ID: a72d4e91c630
Revises: f5c1a8d47b20
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa


revision = "a72d4e91c630"
down_revision = "f5c1a8d47b20"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())

    if "collections" not in existing:
        op.create_table(
            "collections",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False, unique=True),
            sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
            sa.Column("description", sa.Text()),
            sa.Column("banner_image", sa.String(length=512)),
            sa.Column("thumbnail_image", sa.String(length=512)),
            sa.Column("display_order", sa.Integer(), server_default="0"),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
            sa.Column("desktop_banner", sa.String(length=512)),
            sa.Column("mobile_banner", sa.String(length=512)),
            sa.Column("preview_image", sa.String(length=512)),
            sa.Column("highlights", sa.Text()),
            sa.Column("rules", sa.Text()),
            sa.Column("show_on_homepage", sa.Boolean(), server_default=sa.true()),
            sa.Column("subtitle", sa.String(length=255)),
            sa.Column("styling_tips", sa.Text()),
            sa.Column("image", sa.String(length=512)),
        )
        existing.add("collections")

    if "category_banners" not in existing:
        op.create_table(
            "category_banners",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category_id", sa.Integer(), nullable=False, unique=True),
            sa.Column("banner_image", sa.String(length=500), nullable=False),
            sa.Column("title", sa.String(length=255)),
            sa.Column("subtitle", sa.String(length=255)),
            sa.Column("description", sa.Text()),
            sa.Column("button_text", sa.String(length=100)),
            sa.Column("button_link", sa.String(length=255)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
            sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        )

    if "collection_banners" not in existing:
        op.create_table(
            "collection_banners",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("collection_id", sa.Integer(), nullable=False, unique=True),
            sa.Column("banner_image", sa.String(length=500), nullable=False),
            sa.Column("title", sa.String(length=255)),
            sa.Column("subtitle", sa.String(length=255)),
            sa.Column("description", sa.Text()),
            sa.Column("button_text", sa.String(length=100)),
            sa.Column("button_link", sa.String(length=255)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
            sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="CASCADE"),
        )

    if "support_links" not in existing:
        op.create_table(
            "support_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(length=100), nullable=False),
            sa.Column("url", sa.String(length=255), nullable=False),
            sa.Column("icon", sa.String(length=50), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )

    if "site_settings" not in existing:
        op.create_table(
            "site_settings",
            sa.Column("key", sa.String(length=100), primary_key=True),
            sa.Column("value", sa.Text()),
        )


def downgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table_name in ("site_settings", "support_links", "collection_banners", "category_banners", "collections"):
        if table_name in existing:
            op.drop_table(table_name)

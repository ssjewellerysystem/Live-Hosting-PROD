"""add support ticket ownership and conversations

Revision ID: f5c1a8d47b20
Revises: ebb5a7ea1722
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa


revision = "f5c1a8d47b20"
down_revision = "ebb5a7ea1722"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    support_columns = {column["name"] for column in inspector.get_columns("support_messages")}
    support_indexes = {index["name"] for index in inspector.get_indexes("support_messages")}
    support_foreign_keys = inspector.get_foreign_keys("support_messages")
    has_user_foreign_key = any(
        foreign_key.get("referred_table") == "users"
        and foreign_key.get("constrained_columns") == ["user_id"]
        for foreign_key in support_foreign_keys
    )

    with op.batch_alter_table("support_messages") as batch_op:
        if "user_id" not in support_columns:
            batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        if "ix_support_messages_user_id" not in support_indexes:
            batch_op.create_index("ix_support_messages_user_id", ["user_id"], unique=False)
        if not has_user_foreign_key:
            batch_op.create_foreign_key(
                "fk_support_messages_user_id_users",
                "users",
                ["user_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "support_replies" not in tables:
        op.create_table(
            "support_replies",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("support_id", sa.Integer(), nullable=False),
            sa.Column("sender", sa.String(length=100), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["support_id"],
                ["support_messages.id"],
                name="fk_support_replies_support_id_support_messages",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_support_replies_support_id", "support_replies", ["support_id"], unique=False)
    else:
        reply_indexes = {index["name"] for index in inspector.get_indexes("support_replies")}
        if "ix_support_replies_support_id" not in reply_indexes:
            op.create_index("ix_support_replies_support_id", "support_replies", ["support_id"], unique=False)


def downgrade():
    op.drop_index("ix_support_replies_support_id", table_name="support_replies")
    op.drop_table("support_replies")

    with op.batch_alter_table("support_messages") as batch_op:
        batch_op.drop_constraint("fk_support_messages_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_support_messages_user_id")
        batch_op.drop_column("user_id")

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
    with op.batch_alter_table("support_messages") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_support_messages_user_id", ["user_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_support_messages_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )

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


def downgrade():
    op.drop_index("ix_support_replies_support_id", table_name="support_replies")
    op.drop_table("support_replies")

    with op.batch_alter_table("support_messages") as batch_op:
        batch_op.drop_constraint("fk_support_messages_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_support_messages_user_id")
        batch_op.drop_column("user_id")

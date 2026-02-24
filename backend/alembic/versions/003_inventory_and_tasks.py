"""User inventory and user_tasks tables

Revision ID: 003
Revises: 002
Create Date: 2025-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = inspector.get_table_names()
    if "user_inventory" in existing:
        return
    op.create_table(
        "user_inventory",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_inventory_user_id", "user_inventory", ["user_id"], unique=False)
    op.create_unique_constraint("uq_user_inventory_user_item", "user_inventory", ["user_id", "item_type"])

    op.create_table(
        "user_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("required_type_1", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("required_type_2", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("required_type_3", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reward_points", sa.Integer(), nullable=False),
        sa.Column("reward_item_1", sa.Integer(), nullable=False),
        sa.Column("reward_item_2", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_tasks_user_id", "user_tasks", ["user_id"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = inspector.get_table_names()
    if "user_tasks" in existing:
        op.drop_index("ix_user_tasks_user_id", table_name="user_tasks")
        op.drop_table("user_tasks")
    if "user_inventory" in existing:
        op.drop_constraint("uq_user_inventory_user_item", "user_inventory", type_="unique")
        op.drop_index("ix_user_inventory_user_id", table_name="user_inventory")
        op.drop_table("user_inventory")

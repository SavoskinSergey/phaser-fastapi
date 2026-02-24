"""Bonuses and bonus_collections tables

Revision ID: 002
Revises: 001
Create Date: 2025-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = inspector.get_table_names()
    if "bonuses" in existing:
        return  # таблицы уже созданы (например через create_all при старте приложения)
    op.create_table(
        "bonuses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.Integer(), nullable=False),
        sa.Column("tile_x", sa.Integer(), nullable=False),
        sa.Column("tile_y", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "bonus_collections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bonus_id", sa.String(36), sa.ForeignKey("bonuses.id", ondelete="SET NULL"), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("bonus_type", sa.Integer(), nullable=False),
        sa.Column("collected_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bonus_collections_user_id", "bonus_collections", ["user_id"], unique=False)
    op.create_index("ix_bonus_collections_collected_at", "bonus_collections", ["collected_at"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = inspector.get_table_names()
    if "bonus_collections" in existing:
        op.drop_index("ix_bonus_collections_collected_at", table_name="bonus_collections")
        op.drop_index("ix_bonus_collections_user_id", table_name="bonus_collections")
        op.drop_table("bonus_collections")
    if "bonuses" in existing:
        op.drop_table("bonuses")

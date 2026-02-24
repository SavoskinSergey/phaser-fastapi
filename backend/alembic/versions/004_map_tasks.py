"""Map tasks table (tasks on map, shared by all players)

Revision ID: 004
Revises: 003
Create Date: 2025-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "map_tasks" in inspector.get_table_names():
        return
    op.create_table(
        "map_tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tile_x", sa.Integer(), nullable=False),
        sa.Column("tile_y", sa.Integer(), nullable=False),
        sa.Column("required_type_1", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("required_type_2", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("required_type_3", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reward_points", sa.Integer(), nullable=False),
        sa.Column("reward_item_1", sa.Integer(), nullable=False),
        sa.Column("reward_item_2", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_map_tasks_tile", "map_tasks", ["tile_x", "tile_y"], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    if "map_tasks" in sa.inspect(conn).get_table_names():
        op.drop_index("ix_map_tasks_tile", table_name="map_tasks")
        op.drop_table("map_tasks")

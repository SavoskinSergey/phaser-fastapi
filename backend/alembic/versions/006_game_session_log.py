"""Game session log table

Revision ID: 006
Revises: 005
Create Date: 2025-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if "game_session_log" in sa.inspect(conn).get_table_names():
        return
    op.create_table(
        "game_session_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("game_session_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("place", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("is_winner", sa.Integer(), nullable=False),
        sa.Column("played_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_game_session_log_user_id", "game_session_log", ["user_id"], unique=False)
    op.create_index("ix_game_session_log_played_at", "game_session_log", ["played_at"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    if "game_session_log" in sa.inspect(conn).get_table_names():
        op.drop_index("ix_game_session_log_played_at", table_name="game_session_log")
        op.drop_index("ix_game_session_log_user_id", table_name="game_session_log")
        op.drop_table("game_session_log")

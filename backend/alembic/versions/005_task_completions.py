"""Task completions log table

Revision ID: 005
Revises: 004
Create Date: 2025-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if "task_completions" in sa.inspect(conn).get_table_names():
        return
    op.create_table(
        "task_completions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reward_points", sa.Integer(), nullable=False),
        sa.Column("reward_item_1", sa.Integer(), nullable=False),
        sa.Column("reward_item_2", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_task_completions_user_id", "task_completions", ["user_id"], unique=False)
    op.create_index("ix_task_completions_completed_at", "task_completions", ["completed_at"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    if "task_completions" in sa.inspect(conn).get_table_names():
        op.drop_index("ix_task_completions_completed_at", table_name="task_completions")
        op.drop_index("ix_task_completions_user_id", table_name="task_completions")
        op.drop_table("task_completions")

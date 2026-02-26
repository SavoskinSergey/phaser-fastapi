"""Add user experience column

Revision ID: 007
Revises: 006
Create Date: 2025-02-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    if "users" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("users")]
    if "experience" in cols:
        return
    op.add_column("users", sa.Column("experience", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    conn = op.get_bind()
    if "users" in sa.inspect(conn).get_table_names():
        op.drop_column("users", "experience")

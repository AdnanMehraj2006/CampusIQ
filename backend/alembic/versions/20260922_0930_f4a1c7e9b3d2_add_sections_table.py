"""add sections table

Revision ID: f4a1c7e9b3d2
Revises: b3282f0f66ba
Create Date: 2026-09-22 09:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4a1c7e9b3d2'
down_revision: Union[str, Sequence[str], None] = 'b3282f0f66ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=10), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_sections_name"),
    )
    op.create_index(op.f("ix_sections_name"), "sections", ["name"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sections_name"), table_name="sections")
    op.drop_table("sections")

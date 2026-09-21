"""add class_teachers table

Revision ID: b3282f0f66ba
Revises: cc00e40fa87f
Create Date: 2026-09-21 20:15:13.093055
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3282f0f66ba'
down_revision: Union[str, Sequence[str], None] = 'cc00e40fa87f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "class_teachers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("faculty_id", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(length=10), nullable=False),
        sa.Column("semester_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["faculty_id"], ["faculty.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["semester_id"], ["semesters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("faculty_id", "section", "semester_id", name="uq_class_teacher"),
    )
    op.create_index(op.f("ix_class_teachers_faculty_id"), "class_teachers", ["faculty_id"])
    op.create_index(op.f("ix_class_teachers_section"), "class_teachers", ["section"])


def downgrade() -> None:
    op.drop_index(op.f("ix_class_teachers_section"), table_name="class_teachers")
    op.drop_index(op.f("ix_class_teachers_faculty_id"), table_name="class_teachers")
    op.drop_table("class_teachers")

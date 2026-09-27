"""remove section and semester columns

Revision ID: 20260926_1854_xxxx
Revises: 20260923_1430_xxxx_contextual_sections
Create Date: 2026-09-26 18:54:00.000000

"""
from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_1854_xxxx"
down_revision: str | None = "20260923_1430_xxxx_contextual_sections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Remove section/semester from announcements
    with op.batch_alter_table("announcements") as batch_op:
        batch_op.drop_index("ix_announcements_section")
        batch_op.drop_column("section")
        batch_op.drop_column("semester_id")

    # Remove semester_id from subjects
    with op.batch_alter_table("subjects") as batch_op:
        batch_op.drop_index("ix_subjects_semester_id")
        batch_op.drop_column("semester_id")

    # Remove section/semester from students
    with op.batch_alter_table("students") as batch_op:
        batch_op.drop_index("ix_students_section")
        batch_op.drop_index("ix_students_semester_id")
        batch_op.drop_column("section")
        batch_op.drop_column("semester_id")

    # Remove section from assignments
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_index("ix_assignments_section")
        batch_op.drop_column("section")

    # Remove section from timetable
    with op.batch_alter_table("timetable") as batch_op:
        batch_op.drop_index("ix_timetable_section")
        batch_op.drop_index("ix_timetable_semester_id")
        batch_op.drop_index("ix_timetable_section_day_period")
        batch_op.drop_constraint("uq_tt_section_slot")
        batch_op.drop_column("section")
        batch_op.drop_column("semester_id")

    # Remove section from class_teachers
    with op.batch_alter_table("class_teachers") as batch_op:
        batch_op.drop_index("ix_class_teachers_section")
        batch_op.drop_column("section")


def downgrade() -> None:
    # Add section back to class_teachers
    with op.batch_alter_table("class_teachers") as batch_op:
        batch_op.add_column(sa.Column("section", sa.String(length=10), nullable=True))
        batch_op.create_index("ix_class_teachers_section", "section")

    # Add section/semester back to timetable
    with op.batch_alter_table("timetable") as batch_op:
        batch_op.add_column(sa.Column("section", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("semester_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_timetable_section", "section")
        batch_op.create_index("ix_timetable_semester_id", "semester_id")
        batch_op.create_index("ix_timetable_section_day_period", ["section", "day", "period"])
        batch_op.create_unique_constraint("uq_tt_section_slot", ["day", "period", "section", "academic_session_id"])

    # Add section back to assignments
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(sa.Column("section", sa.String(length=10), nullable=True))
        batch_op.create_index("ix_assignments_section", "section")

    # Add section/semester back to students
    with op.batch_alter_table("students") as batch_op:
        batch_op.add_column(sa.Column("section", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("semester_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_students_section", "section")
        batch_op.create_index("ix_students_semester_id", "semester_id")

    # Add semester_id back to subjects
    with op.batch_alter_table("subjects") as batch_op:
        batch_op.add_column(sa.Column("semester_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_subjects_semester_id", "semester_id")

    # Add section/semester back to announcements
    with op.batch_alter_table("announcements") as batch_op:
        batch_op.add_column(sa.Column("section", sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column("semester_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_announcements_section", "section")

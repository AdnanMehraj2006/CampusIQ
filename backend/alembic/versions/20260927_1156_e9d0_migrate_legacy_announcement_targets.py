"""migrate legacy announcement target enum values

Revision ID: 20260927_1156_e9d0
Revises: 20260926_1854_xxxx
Create Date: 2026-09-27 11:56:00.000000

Migrate obsolete SECTION and SEMESTER announcement target values to EVERYONE.
These values existed when Section/Semester architecture was active. Since that
architecture has been removed (target_type now only supports EVERYONE, DEPARTMENT,
COURSE, FACULTY), legacy announcements targeting SECTION or SEMESTER without
valid course_id mappings are migrated to EVERYONE.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260927_1156_e9d0"
down_revision: Union[str, Sequence[str], None] = "20260926_1854_xxxx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update SECTION announcements to EVERYONE (SECTION was deprecated)
    op.execute(
        "UPDATE announcements SET target_type = 'EVERYONE' WHERE target_type = 'SECTION'"
    )
    
    # Update SEMESTER announcements to EVERYONE (SEMESTER was deprecated)
    op.execute(
        "UPDATE announcements SET target_type = 'EVERYONE' WHERE target_type = 'SEMESTER'"
    )


def downgrade() -> None:
    # Downgrade is intentionally NOT implemented as it would reintroduce 
    # obsolete enum values that are no longer supported by the model.
    # This migration is irreversible to prevent data inconsistency.
    pass

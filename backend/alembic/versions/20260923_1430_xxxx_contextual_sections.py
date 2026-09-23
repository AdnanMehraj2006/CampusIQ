"""contextual sections with course/semester FKs

Revision ID: 002609231430
Revises: f4a1c7e9b3d2
Create Date: 2026-09-23 14:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '002609231430'
down_revision: Union[str, Sequence[str], None] = 'f4a1c7e9b3d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add course_id and semester_id columns to sections
    op.add_column('sections', sa.Column('course_id', sa.Integer(), nullable=True))
    op.add_column('sections', sa.Column('semester_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraints
    op.create_foreign_key(
        'fk_sections_course_id', 'sections', 'courses', ['course_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_sections_semester_id', 'sections', 'semesters', ['semester_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Remove the old unique constraint on name
    op.drop_constraint('uq_sections_name', 'sections')
    
    # Create composite unique constraint: same section name allowed across different academic contexts
    op.create_unique_constraint(
        'uq_sections_context', 'sections', ['course_id', 'semester_id', 'name']
    )
    
    # Create indexes for efficient lookups
    op.create_index(op.f('ix_sections_course_id'), 'sections', ['course_id'])
    op.create_index(op.f('ix_sections_semester_id'), 'sections', ['semester_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_sections_semester_id'), table_name='sections')
    op.drop_index(op.f('ix_sections_course_id'), table_name='sections')
    op.drop_constraint('uq_sections_context', 'sections')
    op.create_unique_constraint('uq_sections_name', 'sections', ['name'])
    op.drop_constraint('fk_sections_semester_id', 'sections')
    op.drop_constraint('fk_sections_course_id', 'sections')
    op.drop_column('sections', 'semester_id')
    op.drop_column('sections', 'course_id')
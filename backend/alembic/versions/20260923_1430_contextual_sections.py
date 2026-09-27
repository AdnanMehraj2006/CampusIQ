"""contextual sections with course/semester FKs

Revision ID: c1a2b3c4d5e6
Revises: f4a1c7e9b3d2_widen
Create Date: 2026-09-23 14:30:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "f4a1c7e9b3d2_widen"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add course_id and semester_id columns to sections (if not already present)
    from sqlalchemy import inspect, text
    connection = op.get_bind()
    inspector = inspect(connection)
    columns = [col['name'] for col in inspector.get_columns('sections')]
    
    if 'course_id' not in columns:
        op.add_column('sections', sa.Column('course_id', sa.Integer(), nullable=True))
    if 'semester_id' not in columns:
        op.add_column('sections', sa.Column('semester_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraints (if not already present)
    fks = [fk['name'] for fk in inspector.get_foreign_keys('sections')]
    if 'fk_sections_course_id' not in fks:
        op.create_foreign_key(
            'fk_sections_course_id', 'sections', 'courses', ['course_id'], ['id'],
            ondelete='SET NULL'
        )
    if 'fk_sections_semester_id' not in fks:
        op.create_foreign_key(
            'fk_sections_semester_id', 'sections', 'semesters', ['semester_id'], ['id'],
            ondelete='SET NULL'
        )
    
    # Remove the old unique constraint on name (if exists)
    constraints = [c['name'] for c in inspector.get_unique_constraints('sections')]
    if 'uq_sections_name' in constraints:
        op.drop_constraint('uq_sections_name', 'sections')
    
    # Create composite unique constraint: same section name allowed across different academic contexts
    if 'uq_sections_context' not in constraints:
        op.create_unique_constraint(
            'uq_sections_context', 'sections', ['course_id', 'semester_id', 'name']
        )
    
    # Create indexes for efficient lookups (if not already present)
    indexes = [idx['name'] for idx in inspector.get_indexes('sections')]
    if 'ix_sections_course_id' not in indexes:
        op.create_index(op.f('ix_sections_course_id'), 'sections', ['course_id'])
    if 'ix_sections_semester_id' not in indexes:
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

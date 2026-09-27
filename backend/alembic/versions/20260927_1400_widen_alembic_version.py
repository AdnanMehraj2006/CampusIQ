"""widen alembic_version.version_num column

Revision ID: f4a1c7e9b3d2_widen
Revises: f4a1c7e9b3d2
Create Date: 2026-09-27 14:00:00.000000

Fix migration-chain incompatibility where revision IDs longer than 32 characters
(e.g., 20260923_1430_xxxx_contextual_sections) cannot be stored in the production
database's alembic_version.version_num VARCHAR(32) column.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4a1c7e9b3d2_widen"
down_revision: Union[str, Sequence[str], None] = "f4a1c7e9b3d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen the version_num column to support longer revision IDs
    from alembic import op
    op.execute("ALTER TABLE alembic_version RENAME TO alembic_version_old")
    op.execute("CREATE TABLE alembic_version (version_num VARCHAR(100) NOT NULL PRIMARY KEY)")
    op.execute("INSERT INTO alembic_version SELECT version_num FROM alembic_version_old")
    op.execute("DROP TABLE alembic_version_old")


def downgrade() -> None:
    # Downgrade back to 32 chars (not recommended after longer IDs are in use)
    with op.batch_alter_table("alembic_version") as batch_op:
        batch_op.alter_column(
            "version_num",
            existing_type=sa.String(100),
            type_=sa.String(32),
            existing_nullable=False,
        )

"""Add error_context column to jobs table

Revision: add_error_context
Created: 2024-01-01
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    """Add error_context column to jobs table"""
    op.add_column('jobs', sa.Column('error_context', sa.Text(), nullable=True))


def downgrade():
    """Remove error_context column from jobs table"""
    op.drop_column('jobs', 'error_context')
"""add_updated_at_to_parking_allocations

Revision ID: 2f8594308d71
Revises: 224fabeff6de
Create Date: 2025-12-11 15:47:18.554103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f8594308d71'
down_revision: Union[str, Sequence[str], None] = '224fabeff6de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add updated_at column to parking_allocations table."""
    # Check if column already exists
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    allocations_columns = [col['name'] for col in inspector.get_columns('parking_allocations')]
    
    # Add updated_at column
    if 'updated_at' not in allocations_columns:
        op.add_column('parking_allocations',
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
        )


def downgrade() -> None:
    """Remove updated_at column."""
    op.drop_column('parking_allocations', 'updated_at')

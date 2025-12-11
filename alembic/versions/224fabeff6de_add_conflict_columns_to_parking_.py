"""add_conflict_columns_to_parking_allocations

Revision ID: 224fabeff6de
Revises: 002_add_flight_parking_link
Create Date: 2025-12-11 15:40:35.442850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '224fabeff6de'
down_revision: Union[str, Sequence[str], None] = '002_add_flight_parking_link'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add conflict tracking columns to parking_allocations table."""
    # Check if columns already exist
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    allocations_columns = [col['name'] for col in inspector.get_columns('parking_allocations')]
    
    # Add conflict_detected column
    if 'conflict_detected' not in allocations_columns:
        op.add_column('parking_allocations',
            sa.Column('conflict_detected', sa.Boolean(), server_default=sa.text('false'), nullable=False)
        )
    
    # Add conflict_probability column
    if 'conflict_probability' not in allocations_columns:
        op.add_column('parking_allocations',
            sa.Column('conflict_probability', sa.Float(), nullable=True)
        )
    
    # Add conflict_resolution column
    if 'conflict_resolution' not in allocations_columns:
        op.add_column('parking_allocations',
            sa.Column('conflict_resolution', sa.String(length=200), nullable=True)
        )
    
    # Add updated_at column (required by model)
    if 'updated_at' not in allocations_columns:
        op.add_column('parking_allocations',
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
        )
    
    # Create index on conflict_detected for fast queries
    try:
        op.create_index('idx_allocation_conflict', 'parking_allocations', ['conflict_detected'])
    except Exception:
        pass  # Index may already exist


def downgrade() -> None:
    """Remove conflict tracking columns."""
    op.drop_index('idx_allocation_conflict', 'parking_allocations')
    op.drop_column('parking_allocations', 'updated_at')
    op.drop_column('parking_allocations', 'conflict_resolution')
    op.drop_column('parking_allocations', 'conflict_probability')
    op.drop_column('parking_allocations', 'conflict_detected')

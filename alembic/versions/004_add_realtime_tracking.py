"""Add realtime tracking columns to flights

Revision ID: 004_add_realtime_tracking
Revises: 2f8594308d71, 5cee32faada4
Create Date: 2025-12-15

Adds columns for OpenSky state vectors real-time tracking:
- Position (latitude, longitude)
- Altitude (barometric and geometric)
- Velocity and heading
- Vertical rate
- Ground status
- Last position update timestamp
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004_add_realtime_tracking'
down_revision: Union[str, Sequence[str], None] = ('2f8594308d71', '5cee32faada4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add real-time tracking columns to flights table
    op.add_column('flights', sa.Column('longitude', sa.Float(), nullable=True, comment='Current longitude (decimal degrees)'))
    op.add_column('flights', sa.Column('latitude', sa.Float(), nullable=True, comment='Current latitude (decimal degrees)'))
    op.add_column('flights', sa.Column('baro_altitude', sa.Float(), nullable=True, comment='Barometric altitude (meters)'))
    op.add_column('flights', sa.Column('geo_altitude', sa.Float(), nullable=True, comment='Geometric altitude (meters)'))
    op.add_column('flights', sa.Column('velocity', sa.Float(), nullable=True, comment='Ground speed (m/s)'))
    op.add_column('flights', sa.Column('heading', sa.Float(), nullable=True, comment='True track heading (degrees)'))
    op.add_column('flights', sa.Column('vertical_rate', sa.Float(), nullable=True, comment='Vertical rate (m/s)'))
    op.add_column('flights', sa.Column('on_ground', sa.Boolean(), nullable=True, comment='Aircraft on ground'))
    op.add_column('flights', sa.Column('last_position_update', sa.DateTime(timezone=True), nullable=True, comment='Last state vector update'))
    
    # Create index for position queries
    op.create_index('idx_flight_position', 'flights', ['latitude', 'longitude'], unique=False)
    op.create_index('idx_flight_last_position_update', 'flights', ['last_position_update'], unique=False)


def downgrade() -> None:
    # Remove indexes
    op.drop_index('idx_flight_last_position_update', table_name='flights')
    op.drop_index('idx_flight_position', table_name='flights')
    
    # Remove columns
    op.drop_column('flights', 'last_position_update')
    op.drop_column('flights', 'on_ground')
    op.drop_column('flights', 'vertical_rate')
    op.drop_column('flights', 'heading')
    op.drop_column('flights', 'velocity')
    op.drop_column('flights', 'geo_altitude')
    op.drop_column('flights', 'baro_altitude')
    op.drop_column('flights', 'latitude')
    op.drop_column('flights', 'longitude')

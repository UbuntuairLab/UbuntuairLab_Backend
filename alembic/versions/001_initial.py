"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-12-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('user_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=100), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('role', sa.String(length=20), server_default='user', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_index('idx_users_username', 'users', ['username'], unique=True)
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
    
    # Create flights table
    op.create_table('flights',
    sa.Column('icao24', sa.String(length=6), nullable=False),
    sa.Column('callsign', sa.String(length=8), nullable=True),
    sa.Column('origin_country', sa.String(length=100), nullable=True),
    sa.Column('flight_type', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='scheduled', nullable=False),
    sa.Column('departure_airport', sa.String(length=4), nullable=True),
    sa.Column('arrival_airport', sa.String(length=4), nullable=True),
    sa.Column('first_seen', sa.Integer(), nullable=False),
    sa.Column('last_seen', sa.Integer(), nullable=False),
    sa.Column('predicted_eta', sa.DateTime(timezone=True), nullable=True),
    sa.Column('predicted_etd', sa.DateTime(timezone=True), nullable=True),
    sa.Column('predicted_delay_minutes', sa.Integer(), nullable=True),
    sa.Column('predicted_occupation_minutes', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('icao24')
    )
    op.create_index('idx_flight_status_type', 'flights', ['status', 'flight_type'])
    op.create_index('idx_flight_airports', 'flights', ['departure_airport', 'arrival_airport'])
    op.create_index('idx_flight_timestamps', 'flights', ['first_seen', 'last_seen'])
    
    # Create parking_spots table
    op.create_table('parking_spots',
    sa.Column('spot_id', sa.String(length=10), nullable=False),
    sa.Column('spot_number', sa.Integer(), nullable=False),
    sa.Column('spot_type', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='available', nullable=False),
    sa.Column('aircraft_size_capacity', sa.String(length=20), nullable=False),
    sa.Column('has_jetway', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('distance_to_terminal', sa.Integer(), nullable=False),
    sa.Column('admin_configurable', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('spot_id')
    )
    op.create_index('idx_spot_type_status', 'parking_spots', ['spot_type', 'status'])
    
    # Create parking_allocations table
    op.create_table('parking_allocations',
    sa.Column('allocation_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('flight_icao24', sa.String(length=6), nullable=False),
    sa.Column('spot_id', sa.String(length=10), nullable=False),
    sa.Column('allocated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('predicted_duration_minutes', sa.Integer(), nullable=False),
    sa.Column('predicted_end_time', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actual_start_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('actual_end_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('actual_duration_minutes', sa.Integer(), nullable=True),
    sa.Column('overflow_to_military', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('overflow_reason', sa.String(length=200), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['flight_icao24'], ['flights.icao24'], ),
    sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.spot_id'], ),
    sa.PrimaryKeyConstraint('allocation_id')
    )
    op.create_index('idx_allocation_flight', 'parking_allocations', ['flight_icao24'])
    op.create_index('idx_allocation_spot', 'parking_allocations', ['spot_id'])
    op.create_index('idx_allocation_active', 'parking_allocations', ['is_active', 'spot_id'])
    
    # Create ai_predictions table
    op.create_table('ai_predictions',
    sa.Column('prediction_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('flight_icao24', sa.String(length=6), nullable=False),
    sa.Column('model_type', sa.String(length=20), nullable=False),
    sa.Column('model_version', sa.String(length=50), nullable=True),
    sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('cached', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('execution_time_ms', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['flight_icao24'], ['flights.icao24'], ),
    sa.PrimaryKeyConstraint('prediction_id')
    )
    op.create_index('idx_prediction_flight', 'ai_predictions', ['flight_icao24'])
    op.create_index('idx_prediction_model', 'ai_predictions', ['model_type', 'flight_icao24'])


def downgrade() -> None:
    op.drop_table('ai_predictions')
    op.drop_table('parking_allocations')
    op.drop_table('parking_spots')
    op.drop_table('flights')
    op.drop_table('users')

"""Add flight parking link and notifications

Revision ID: 002_add_flight_parking_link
Revises: 001_initial
Create Date: 2025-12-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_flight_parking_link'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add parking_spot_id to flights table (check if column already exists)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    flights_columns = [col['name'] for col in inspector.get_columns('flights')]
    
    if 'parking_spot_id' not in flights_columns:
        op.add_column('flights',
            sa.Column('parking_spot_id', sa.String(length=20), nullable=True)
        )
        op.create_foreign_key(
            'fk_flights_parking_spot',
            'flights', 'parking_spots',
            ['parking_spot_id'], ['spot_id'],
            ondelete='SET NULL'
        )
        op.create_index('idx_flights_parking_spot', 'flights', ['parking_spot_id'])
    
    # Add est_departure_time and est_arrival_time to flights
    if 'est_departure_time' not in flights_columns:
        op.add_column('flights',
            sa.Column('est_departure_time', sa.DateTime(timezone=True), nullable=True)
        )
    if 'est_arrival_time' not in flights_columns:
        op.add_column('flights',
            sa.Column('est_arrival_time', sa.DateTime(timezone=True), nullable=True)
        )
    
    # Create notifications table (check if table exists)
    existing_tables = inspector.get_table_names()
    
    if 'notifications' not in existing_tables:
        op.create_table('notifications',
            sa.Column('notification_id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('flight_icao24', sa.String(length=6), nullable=False),
            sa.Column('notification_type', sa.String(length=20), nullable=False),
            sa.Column('severity', sa.String(length=20), server_default='INFO', nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('read_status', sa.Boolean(), server_default=sa.text('false'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('notification_id'),
            sa.ForeignKeyConstraint(['flight_icao24'], ['flights.icao24'], ondelete='CASCADE')
        )
        op.create_index('idx_notifications_flight', 'notifications', ['flight_icao24'])
        op.create_index('idx_notifications_type', 'notifications', ['notification_type'])
        op.create_index('idx_notifications_read_status', 'notifications', ['read_status'])
        op.create_index('idx_notifications_created_at', 'notifications', ['created_at'])
    
    # Create aircraft_turnaround_rules table (check if table exists)
    if 'aircraft_turnaround_rules' not in existing_tables:
        op.create_table('aircraft_turnaround_rules',
            sa.Column('rule_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('aircraft_type', sa.String(length=10), nullable=False),
            sa.Column('min_turnaround_minutes', sa.Integer(), nullable=False),
            sa.Column('avg_turnaround_minutes', sa.Integer(), nullable=False),
            sa.Column('max_turnaround_minutes', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('rule_id'),
            sa.UniqueConstraint('aircraft_type')
        )
        op.create_index('idx_turnaround_aircraft_type', 'aircraft_turnaround_rules', ['aircraft_type'], unique=True)
        
        # Seed turnaround rules with common aircraft types
        op.execute("""
            INSERT INTO aircraft_turnaround_rules (aircraft_type, min_turnaround_minutes, avg_turnaround_minutes, max_turnaround_minutes)
            VALUES
                ('A320', 45, 60, 90),
                ('A321', 50, 65, 95),
                ('A319', 40, 55, 85),
                ('A330', 60, 90, 120),
                ('A350', 70, 100, 130),
                ('B737', 45, 60, 90),
                ('B747', 75, 110, 150),
                ('B777', 70, 100, 130),
                ('B787', 65, 95, 125),
                ('E190', 35, 50, 75),
                ('DEFAULT', 45, 60, 90)
            ON CONFLICT (aircraft_type) DO NOTHING;
        """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('aircraft_turnaround_rules')
    op.drop_table('notifications')
    
    # Remove columns from flights
    op.drop_constraint('fk_flights_parking_spot', 'flights', type_='foreignkey')
    op.drop_index('idx_flights_parking_spot', 'flights')
    op.drop_column('flights', 'parking_spot_id')
    op.drop_column('flights', 'est_departure_time')
    op.drop_column('flights', 'est_arrival_time')

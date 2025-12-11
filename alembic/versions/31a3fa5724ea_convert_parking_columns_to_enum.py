"""convert_parking_columns_to_enum

Revision ID: 31a3fa5724ea
Revises: 003_seed_parking_spots
Create Date: 2025-12-11 16:14:16.435046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31a3fa5724ea'
down_revision: Union[str, Sequence[str], None] = '2f8594308d71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert string columns to PostgreSQL ENUM types."""
    
    # Drop existing enum types if they exist
    op.execute("DROP TYPE IF EXISTS spottype CASCADE")
    op.execute("DROP TYPE IF EXISTS spotstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS aircraftsizecategory CASCADE")
    
    # Create new ENUM types with correct values
    op.execute("CREATE TYPE spottype AS ENUM ('civil', 'military')")
    op.execute("CREATE TYPE spotstatus AS ENUM ('available', 'occupied', 'reserved', 'maintenance')")
    op.execute("CREATE TYPE aircraftsizecategory AS ENUM ('small', 'medium', 'large')")
    
    # Drop default values first
    op.execute("ALTER TABLE parking_spots ALTER COLUMN status DROP DEFAULT")
    
    # Convert parking_spots.spot_type (convert CIVIL -> civil, MILITARY -> military)
    op.execute("""
        ALTER TABLE parking_spots 
        ALTER COLUMN spot_type TYPE spottype 
        USING LOWER(spot_type)::spottype
    """)
    
    # Convert parking_spots.status (convert to lowercase)
    op.execute("""
        ALTER TABLE parking_spots 
        ALTER COLUMN status TYPE spotstatus 
        USING LOWER(status)::spotstatus
    """)
    
    # Convert parking_spots.aircraft_size_capacity (convert to lowercase)
    op.execute("""
        ALTER TABLE parking_spots 
        ALTER COLUMN aircraft_size_capacity TYPE aircraftsizecategory 
        USING LOWER(aircraft_size_capacity)::aircraftsizecategory
    """)
    
    # Re-add default value with enum cast
    op.execute("ALTER TABLE parking_spots ALTER COLUMN status SET DEFAULT 'available'::spotstatus")


def downgrade() -> None:
    """Revert ENUM types back to strings."""
    
    # Convert back to strings
    op.execute("ALTER TABLE parking_spots ALTER COLUMN spot_type TYPE VARCHAR(20)")
    op.execute("ALTER TABLE parking_spots ALTER COLUMN status TYPE VARCHAR(20)")
    op.execute("ALTER TABLE parking_spots ALTER COLUMN aircraft_size_capacity TYPE VARCHAR(20)")
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS spottype")
    op.execute("DROP TYPE IF EXISTS spotstatus")
    op.execute("DROP TYPE IF EXISTS aircraftsizecategory")

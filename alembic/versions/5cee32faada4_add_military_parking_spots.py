"""add_military_parking_spots

Revision ID: 5cee32faada4
Revises: 003_seed_parking_spots
Create Date: 2025-12-11 16:35:59.325782

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5cee32faada4'
down_revision: Union[str, Sequence[str], None] = '003_seed_parking_spots'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add military overflow parking spots."""
    op.execute("""
        INSERT INTO parking_spots (spot_id, spot_number, spot_type, status, aircraft_size_capacity, has_jetway, distance_to_terminal, admin_configurable, notes) VALUES
            -- M spots (Military overflow spots for saturation management)
            ('M1', 17, 'military'::spottype, 'available'::spotstatus, 'large'::aircraftsizecategory, false, 400, false, 'Military Zone - Overflow 1'),
            ('M2', 18, 'military'::spottype, 'available'::spotstatus, 'large'::aircraftsizecategory, false, 420, false, 'Military Zone - Overflow 2'),
            ('M3', 19, 'military'::spottype, 'available'::spotstatus, 'medium'::aircraftsizecategory, false, 440, false, 'Military Zone - Overflow 3'),
            ('M4', 20, 'military'::spottype, 'available'::spotstatus, 'medium'::aircraftsizecategory, false, 460, false, 'Military Zone - Overflow 4'),
            ('M5', 21, 'military'::spottype, 'available'::spotstatus, 'small'::aircraftsizecategory, false, 480, false, 'Military Zone - Overflow 5')
        ON CONFLICT (spot_id) DO NOTHING;
    """)


def downgrade() -> None:
    """Remove military overflow parking spots."""
    op.execute("""
        DELETE FROM parking_spots 
        WHERE spot_id IN ('M1', 'M2', 'M3', 'M4', 'M5');
    """)

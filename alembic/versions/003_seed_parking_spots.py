"""Seed parking spots

Revision ID: 003_seed_parking_spots
Revises: 2f8594308d71
Create Date: 2025-12-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_seed_parking_spots'
down_revision: Union[str, None] = '31a3fa5724ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed 16 civil parking spots (P1-P5, S1-S10B)"""
    # First ensure enum values match (cast to text to avoid enum issues)
    op.execute("""
        INSERT INTO parking_spots (spot_id, spot_number, spot_type, status, aircraft_size_capacity, has_jetway, distance_to_terminal, admin_configurable, notes)
        VALUES
            -- P spots (5 civil spots with jetways)
            ('P1', 1, 'civil'::spottype, 'available'::spotstatus, 'large'::aircraftsizecategory, true, 50, true, 'Zone P - Contact 1'),
            ('P2', 2, 'civil'::spottype, 'available'::spotstatus, 'large'::aircraftsizecategory, true, 60, true, 'Zone P - Contact 2'),
            ('P3', 3, 'civil'::spottype, 'available'::spotstatus, 'medium'::aircraftsizecategory, true, 70, true, 'Zone P - Contact 3'),
            ('P4', 4, 'civil'::spottype, 'available'::spotstatus, 'medium'::aircraftsizecategory, true, 80, true, 'Zone P - Contact 4'),
            ('P5', 5, 'civil'::spottype, 'available'::spotstatus, 'large'::aircraftsizecategory, true, 90, true, 'Zone P - Contact 5'),
            
            -- S spots (11 civil spots remote parking)
            ('S1', 6, 'civil'::spottype, 'available'::spotstatus, 'medium'::aircraftsizecategory, false, 200, true, 'Zone S - Remote 1'),
            ('S2', 7, 'civil'::spottype, 'available'::spotstatus, 'medium'::aircraftsizecategory, false, 210, true, 'Zone S - Remote 2'),
            ('S3', 8, 'civil'::spottype, 'available'::spotstatus, 'medium'::aircraftsizecategory, false, 220, true, 'Zone S - Remote 3'),
            ('S4', 9, 'civil'::spottype, 'available'::spotstatus, 'small'::aircraftsizecategory, false, 230, true, 'Zone S - Remote 4'),
            ('S5', 10, 'civil'::spottype, 'available'::spotstatus, 'small'::aircraftsizecategory, false, 240, true, 'Zone S - Remote 5'),
            ('S6', 11, 'civil'::spottype, 'available'::spotstatus, 'medium'::aircraftsizecategory, false, 250, true, 'Zone S - Remote 6'),
            ('S7', 12, 'civil'::spottype, 'available'::spotstatus, 'medium'::aircraftsizecategory, false, 260, true, 'Zone S - Remote 7'),
            ('S8', 13, 'civil'::spottype, 'available'::spotstatus, 'large'::aircraftsizecategory, false, 270, true, 'Zone S - Remote 8'),
            ('S9', 14, 'civil'::spottype, 'available'::spotstatus, 'large'::aircraftsizecategory, false, 280, true, 'Zone S - Remote 9'),
            ('S10A', 15, 'civil'::spottype, 'available'::spotstatus, 'small'::aircraftsizecategory, false, 290, true, 'Zone S - Remote 10A'),
            ('S10B', 16, 'civil'::spottype, 'available'::spotstatus, 'small'::aircraftsizecategory, false, 295, true, 'Zone S - Remote 10B')
        ON CONFLICT (spot_id) DO NOTHING;
    """)


def downgrade() -> None:
    """Remove seeded parking spots"""
    op.execute("""
        DELETE FROM parking_spots 
        WHERE spot_id IN ('P1', 'P2', 'P3', 'P4', 'P5', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'S10A', 'S10B');
    """)

"""Initial Migration

Revision ID: 483839a606cf
Revises: 
Create Date: 2024-11-08 15:16:08.916821

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '483839a606cf'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """This migration is already applied to your database"""
    # Since your database is already at this revision,
    # we don't need to create any tables here
    pass


def downgrade():
    """Downgrade from initial state"""
    # This would drop all tables if needed
    pass
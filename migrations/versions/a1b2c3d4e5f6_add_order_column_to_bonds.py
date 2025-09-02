"""Add order column to bonds table

Revision ID: a1b2c3d4e5f6
Revises: f5a6b7c8d9e0
Create Date: 2025-08-19 00:46:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    """Add order column to bonds table"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Check if bonds table exists
    if 'bonds' in inspector.get_table_names():
        try:
            # Add order column to bonds table
            op.add_column('bonds', sa.Column('order', sa.Integer(), nullable=True))
            
            # Create index for the order column
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('bonds')]
            if 'idx_bonds_order' not in existing_indexes:
                op.create_index('idx_bonds_order', 'bonds', ['order'])
                
        except Exception as e:
            print(f"Error adding order column to bonds: {e}")


def downgrade():
    """Remove order column from bonds table"""
    try:
        # Drop index first
        op.drop_index('idx_bonds_order', 'bonds')
        
        # Remove order column
        op.drop_column('bonds', 'order')
        
    except Exception as e:
        print(f"Error removing order column from bonds: {e}")
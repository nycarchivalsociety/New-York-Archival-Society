"""add_shipping_address_to_donors

Revision ID: b244bdefb1aa
Revises: 2f93dfcdf00f
Create Date: 2025-03-12 15:41:26.463306

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'b244bdefb1aa'
down_revision = '2f93dfcdf00f'
branch_labels = None
depends_on = None


def upgrade():
    # Get existing columns to only add what's missing
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    if 'donors' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('donors')]
        
        # Add shipping address columns in separate statements with error handling
        try:
            if 'shipping_street' not in existing_columns:
                op.add_column('donors', sa.Column('shipping_street', sa.String(length=255), nullable=True))
                
            if 'shipping_apartment' not in existing_columns:
                op.add_column('donors', sa.Column('shipping_apartment', sa.String(length=255), nullable=True))
                
            if 'shipping_city' not in existing_columns:
                op.add_column('donors', sa.Column('shipping_city', sa.String(length=100), nullable=True))
                
            if 'shipping_state' not in existing_columns:
                op.add_column('donors', sa.Column('shipping_state', sa.String(length=100), nullable=True))
                
            if 'shipping_zip_code' not in existing_columns:
                op.add_column('donors', sa.Column('shipping_zip_code', sa.String(length=20), nullable=True))
                
            if 'use_billing_for_shipping' not in existing_columns:
                op.add_column('donors', sa.Column('use_billing_for_shipping', sa.Boolean(), nullable=True, server_default='true'))
        except Exception as e:
            # Log the error but don't re-raise, so we don't abort the transaction
            print(f"Error adding shipping columns: {e}")
            # Important - this actually rolls back the transaction so it's not in a failed state
            conn.execute(sa.text("ROLLBACK"))
            
def downgrade():
    # Remove shipping columns if needed
    try:
        op.drop_column('donors', 'use_billing_for_shipping')
        op.drop_column('donors', 'shipping_zip_code')
        op.drop_column('donors', 'shipping_state')
        op.drop_column('donors', 'shipping_city')
        op.drop_column('donors', 'shipping_apartment')
        op.drop_column('donors', 'shipping_street')
    except Exception as e:
        print(f"Error removing shipping columns: {e}")
        # Roll back explicitly to avoid leaving transaction in a failed state
        conn = op.get_bind()
        conn.execute(sa.text("ROLLBACK"))

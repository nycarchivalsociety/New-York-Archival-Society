"""bonds table and restructure of old tables

Revision ID: 2f93dfcdf00f
Revises: 483839a606cf
Create Date: 2025-01-22 11:41:05.391626
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = '2f93dfcdf00f'
down_revision = '483839a606cf'
branch_labels = None
depends_on = None

def upgrade():
    # Get all existing tables
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    # Rename items table to historical_records only if it exists
    if 'items' in tables:
        op.rename_table('items', 'historical_records')
    
    # Add address columns to donors only if table exists and columns don't exist
    if 'donors' in tables:
        columns_to_add = {
            'street': sa.Column('street', sa.String(length=255), nullable=True),
            'apartment': sa.Column('apartment', sa.String(length=255), nullable=True),
            'city': sa.Column('city', sa.String(length=100), nullable=True),
            'state': sa.Column('state', sa.String(length=100), nullable=True),
            'zip_code': sa.Column('zip_code', sa.String(length=20), nullable=True)
        }
        
        existing_columns = inspector.get_columns('donors')
        existing_column_names = {col['name'] for col in existing_columns}
        
        with op.batch_alter_table('donors', schema=None) as batch_op:
            for col_name, col_def in columns_to_add.items():
                if col_name not in existing_column_names:
                    batch_op.add_column(col_def)
    
    # Update transactions table item_id - only if table exists
    if 'transactions' in tables:
        with op.batch_alter_table('transactions', schema=None) as batch_op:
            # Check if constraint exists before trying to drop it
            for fk in inspector.get_foreign_keys('transactions'):
                if fk.get('name') == 'transactions_item_id_fkey':
                    batch_op.drop_constraint('transactions_item_id_fkey', type_='foreignkey')
                    break
                    
            batch_op.alter_column('item_id',
                existing_type=sa.UUID(),
                type_=sa.String(length=255),
                existing_nullable=False)
    
    # Create bonds table only if it doesn't exist
    if 'bonds' not in tables:
        op.create_table('bonds',
            sa.Column('bond_id', sa.String(length=255), nullable=False),
            sa.Column('retail_price', sa.Numeric(), nullable=True),
            sa.Column('par_value', sa.String(length=255), nullable=True),
            sa.Column('issue_date', sa.Date(), nullable=True),
            sa.Column('due_date', sa.Date(), nullable=True),
            sa.Column('mayor', sa.String(length=100), nullable=True),
            sa.Column('comptroller', sa.String(length=100), nullable=True),
            sa.Column('size', sa.String(length=50), nullable=True),
            sa.Column('front_image', sa.String(length=255), nullable=True),
            sa.Column('back_image', sa.String(length=255), nullable=True),
            sa.Column('status', sa.Text(), nullable=False, server_default="available"),
            sa.Column('type', sa.String(length=100), nullable=True),
            sa.Column('purpose_of_bond', sa.Text(), nullable=True),
            sa.Column('vignette', sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint('bond_id')
        )

def downgrade():
    # Get all existing tables
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    # Revert all changes in reverse order - only if tables exist
    if 'bonds' in tables:
        op.drop_table('bonds')
    
    if 'transactions' in tables:
        with op.batch_alter_table('transactions', schema=None) as batch_op:
            batch_op.alter_column('item_id',
                existing_type=sa.String(length=255),
                type_=sa.UUID(),
                existing_nullable=False)
            
            # Only create foreign key if the items table exists after rename
            if 'items' in tables:
                batch_op.create_foreign_key(
                    'transactions_item_id_fkey',
                    'items',
                    ['item_id'],
                    ['id']
                )
    
    if 'donors' in tables:
        with op.batch_alter_table('donors', schema=None) as batch_op:
            batch_op.drop_column('zip_code')
            batch_op.drop_column('state')
            batch_op.drop_column('city')
            batch_op.drop_column('apartment')
            batch_op.drop_column('street')
    
    # Only rename back if historical_records exists
    if 'historical_records' in tables:
        op.rename_table('historical_records', 'items')
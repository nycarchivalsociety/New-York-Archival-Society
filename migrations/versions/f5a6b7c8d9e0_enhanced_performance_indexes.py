"""Enhanced performance indexes and optimizations

Revision ID: f5a6b7c8d9e0
Revises: c8f9a2b3d4e5
Create Date: 2025-08-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f5a6b7c8d9e0'
down_revision = 'c8f9a2b3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    """Add enhanced performance indexes and optimizations"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Enhanced indexes for historical_records table
    if 'historical_records' in inspector.get_table_names():
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('historical_records')]
        
        try:
            # Compound index for common pagination queries (adopted + created_at for sorting)
            if 'idx_historical_records_adopted_created_at' not in existing_indexes:
                op.create_index(
                    'idx_historical_records_adopted_created_at', 
                    'historical_records', 
                    ['adopted', 'created_at'],
                    postgresql_using='btree'
                )
            
            # Compound index for fee-based filtering with adoption status
            if 'idx_historical_records_adopted_fee' not in existing_indexes:
                op.create_index(
                    'idx_historical_records_adopted_fee', 
                    'historical_records', 
                    ['adopted', 'fee'],
                    postgresql_using='btree'
                )
            
            # Text search index for name field (for search functionality)
            if 'idx_historical_records_name_trgm' not in existing_indexes:
                # Create trigram index for partial text search
                op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
                op.create_index(
                    'idx_historical_records_name_trgm',
                    'historical_records',
                    ['name'],
                    postgresql_using='gin',
                    postgresql_ops={'name': 'gin_trgm_ops'}
                )
            
            # Covering index for list views (includes commonly selected columns)
            if 'idx_historical_records_list_covering' not in existing_indexes:
                op.create_index(
                    'idx_historical_records_list_covering',
                    'historical_records',
                    ['adopted', 'created_at'],
                    postgresql_include=['id', 'name', 'fee', 'imgurl', 'description']
                )
                
        except Exception as e:
            print(f"Error adding historical_records indexes: {e}")
    
    # Enhanced indexes for bonds table
    if 'bonds' in inspector.get_table_names():
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('bonds')]
        
        try:
            # Compound index for status + issue_date (most common query pattern)
            if 'idx_bonds_status_issue_date' not in existing_indexes:
                op.create_index(
                    'idx_bonds_status_issue_date',
                    'bonds',
                    ['status', 'issue_date'],
                    postgresql_using='btree'
                )
            
            # Compound index for status + type + issue_date (for filtered queries)
            if 'idx_bonds_status_type_issue_date' not in existing_indexes:
                op.create_index(
                    'idx_bonds_status_type_issue_date',
                    'bonds',
                    ['status', 'type', 'issue_date'],
                    postgresql_using='btree'
                )
            
            # Price range index for bonds filtering
            if 'idx_bonds_retail_price_range' not in existing_indexes:
                op.create_index(
                    'idx_bonds_retail_price_range',
                    'bonds',
                    ['retail_price'],
                    postgresql_where='retail_price IS NOT NULL'
                )
            
            # Year-based partial index for common date range queries
            if 'idx_bonds_issue_year' not in existing_indexes:
                op.execute("""
                    CREATE INDEX idx_bonds_issue_year ON bonds 
                    (EXTRACT(year FROM issue_date))
                    WHERE issue_date IS NOT NULL
                """)
            
            # Covering index for bond list views
            if 'idx_bonds_list_covering' not in existing_indexes:
                op.create_index(
                    'idx_bonds_list_covering',
                    'bonds',
                    ['status', 'issue_date'],
                    postgresql_include=['bond_id', 'retail_price', 'type', 'front_image', 'back_image']
                )
                
        except Exception as e:
            print(f"Error adding bonds indexes: {e}")
    
    # Enhanced indexes for transactions table
    if 'transactions' in inspector.get_table_names():
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('transactions')]
        
        try:
            # Compound index for donor transaction history
            if 'idx_transactions_donor_timestamp_status' not in existing_indexes:
                op.create_index(
                    'idx_transactions_donor_timestamp_status',
                    'transactions',
                    ['donor_id', 'timestamp', 'payment_status'],
                    postgresql_using='btree'
                )
            
            # Item-based transaction tracking
            if 'idx_transactions_item_timestamp' not in existing_indexes:
                op.create_index(
                    'idx_transactions_item_timestamp',
                    'transactions',
                    ['item_id', 'timestamp'],
                    postgresql_using='btree'
                )
            
            # Date range queries optimization
            if 'idx_transactions_timestamp_date' not in existing_indexes:
                op.execute("""
                    CREATE INDEX idx_transactions_timestamp_date ON transactions 
                    (DATE(timestamp), payment_status)
                    WHERE payment_status = 'COMPLETED'
                """)
            
            # Email-based lookup optimization
            if 'idx_transactions_donor_email_lower' not in existing_indexes:
                op.execute("""
                    CREATE INDEX idx_transactions_donor_email_lower ON transactions 
                    (LOWER(donor_email))
                    WHERE donor_email IS NOT NULL
                """)
                
        except Exception as e:
            print(f"Error adding transactions indexes: {e}")
    
    # Enhanced indexes for donors table
    if 'donors' in inspector.get_table_names():
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('donors')]
        
        try:
            # Case-insensitive email index
            if 'idx_donors_email_lower' not in existing_indexes:
                op.execute("""
                    CREATE UNIQUE INDEX idx_donors_email_lower ON donors 
                    (LOWER(donor_email))
                    WHERE donor_email IS NOT NULL
                """)
            
            # Name search optimization
            if 'idx_donors_name_trgm' not in existing_indexes:
                op.create_index(
                    'idx_donors_name_trgm',
                    'donors',
                    ['donor_name'],
                    postgresql_using='gin',
                    postgresql_ops={'donor_name': 'gin_trgm_ops'}
                )
            
            # Location-based index for shipping
            if 'idx_donors_location' not in existing_indexes:
                op.create_index(
                    'idx_donors_location',
                    'donors',
                    ['shipping_state', 'shipping_city'],
                    postgresql_where='shipping_state IS NOT NULL AND shipping_city IS NOT NULL'
                )
                
        except Exception as e:
            print(f"Error adding donors indexes: {e}")
    
    # Enhanced indexes for donor_item table
    if 'donor_item' in inspector.get_table_names():
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('donor_item')]
        
        try:
            # Compound index for relationship queries
            if 'idx_donor_item_donor_item' not in existing_indexes:
                op.create_index(
                    'idx_donor_item_donor_item',
                    'donor_item',
                    ['donor_id', 'item_id'],
                    unique=True
                )
            
            # Item-based lookup for adoption queries
            if 'idx_donor_item_item_donor' not in existing_indexes:
                op.create_index(
                    'idx_donor_item_item_donor',
                    'donor_item',
                    ['item_id', 'donor_id']
                )
                
        except Exception as e:
            print(f"Error adding donor_item indexes: {e}")


def downgrade():
    """Remove enhanced performance indexes"""
    
    # Remove donor_item indexes
    try:
        op.drop_index('idx_donor_item_item_donor', 'donor_item')
        op.drop_index('idx_donor_item_donor_item', 'donor_item')
    except Exception as e:
        print(f"Error removing donor_item indexes: {e}")
    
    # Remove donors indexes
    try:
        op.drop_index('idx_donors_location', 'donors')
        op.drop_index('idx_donors_name_trgm', 'donors')
        op.drop_index('idx_donors_email_lower', 'donors')
    except Exception as e:
        print(f"Error removing donors indexes: {e}")
    
    # Remove transactions indexes
    try:
        op.execute("DROP INDEX IF EXISTS idx_transactions_donor_email_lower")
        op.execute("DROP INDEX IF EXISTS idx_transactions_timestamp_date")
        op.drop_index('idx_transactions_item_timestamp', 'transactions')
        op.drop_index('idx_transactions_donor_timestamp_status', 'transactions')
    except Exception as e:
        print(f"Error removing transactions indexes: {e}")
    
    # Remove bonds indexes
    try:
        op.drop_index('idx_bonds_list_covering', 'bonds')
        op.execute("DROP INDEX IF EXISTS idx_bonds_issue_year")
        op.drop_index('idx_bonds_retail_price_range', 'bonds')
        op.drop_index('idx_bonds_status_type_issue_date', 'bonds')
        op.drop_index('idx_bonds_status_issue_date', 'bonds')
    except Exception as e:
        print(f"Error removing bonds indexes: {e}")
    
    # Remove historical_records indexes
    try:
        op.drop_index('idx_historical_records_list_covering', 'historical_records')
        op.drop_index('idx_historical_records_name_trgm', 'historical_records')
        op.drop_index('idx_historical_records_adopted_fee', 'historical_records')
        op.drop_index('idx_historical_records_adopted_created_at', 'historical_records')
    except Exception as e:
        print(f"Error removing historical_records indexes: {e}")
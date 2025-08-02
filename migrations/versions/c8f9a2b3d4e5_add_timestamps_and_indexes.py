"""add_timestamps_and_indexes

Revision ID: c8f9a2b3d4e5
Revises: b244bdefb1aa
Create Date: 2025-08-02 11:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c8f9a2b3d4e5'
down_revision = 'b244bdefb1aa'
branch_labels = None
depends_on = None


def upgrade():
    """Add timestamp columns and performance indexes to all tables"""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Add timestamp columns to historical_records table
    if 'historical_records' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('historical_records')]
        
        try:
            if 'created_at' not in existing_columns:
                op.add_column('historical_records', 
                    sa.Column('created_at', sa.DateTime(timezone=True), 
                             server_default=sa.text('now()'), nullable=False))
                
            if 'updated_at' not in existing_columns:
                op.add_column('historical_records', 
                    sa.Column('updated_at', sa.DateTime(timezone=True), 
                             server_default=sa.text('now()'), nullable=False))
                
            # Add indexes for historical_records
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('historical_records')]
            
            if 'idx_historical_records_name' not in existing_indexes:
                op.create_index('idx_historical_records_name', 'historical_records', ['name'])
                
            if 'idx_historical_records_adopted' not in existing_indexes:
                op.create_index('idx_historical_records_adopted', 'historical_records', ['adopted'])
                
            if 'idx_historical_records_adopted_name' not in existing_indexes:
                op.create_index('idx_historical_records_adopted_name', 'historical_records', ['adopted', 'name'])
                
            if 'idx_historical_records_fee' not in existing_indexes:
                op.create_index('idx_historical_records_fee', 'historical_records', ['fee'])
                
            # Add check constraints
            try:
                op.create_check_constraint('check_positive_fee', 'historical_records', 'fee > 0')
            except:
                pass  # Constraint might already exist
                
            try:
                op.create_check_constraint('check_name_not_empty', 'historical_records', 'char_length(name) > 0')
            except:
                pass  # Constraint might already exist
                
        except Exception as e:
            print(f"Error updating historical_records: {e}")
    
    # Add timestamp columns to donors table
    if 'donors' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('donors')]
        
        try:
            if 'created_at' not in existing_columns:
                op.add_column('donors', 
                    sa.Column('created_at', sa.DateTime(timezone=True), 
                             server_default=sa.text('now()'), nullable=False))
                
            if 'updated_at' not in existing_columns:
                op.add_column('donors', 
                    sa.Column('updated_at', sa.DateTime(timezone=True), 
                             server_default=sa.text('now()'), nullable=False))
                
            # Add indexes for donors
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('donors')]
            
            if 'idx_donors_name' not in existing_indexes:
                op.create_index('idx_donors_name', 'donors', ['donor_name'])
                
            if 'idx_donors_email' not in existing_indexes:
                op.create_index('idx_donors_email', 'donors', ['donor_email'])
                
        except Exception as e:
            print(f"Error updating donors: {e}")
    
    # Add timestamp columns to bonds table
    if 'bonds' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('bonds')]
        
        try:
            if 'created_at' not in existing_columns:
                op.add_column('bonds', 
                    sa.Column('created_at', sa.DateTime(timezone=True), 
                             server_default=sa.text('now()'), nullable=False))
                
            if 'updated_at' not in existing_columns:
                op.add_column('bonds', 
                    sa.Column('updated_at', sa.DateTime(timezone=True), 
                             server_default=sa.text('now()'), nullable=False))
                
            # Add indexes for bonds
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('bonds')]
            
            if 'idx_bonds_issue_date' not in existing_indexes:
                op.create_index('idx_bonds_issue_date', 'bonds', ['issue_date'])
                
            if 'idx_bonds_status' not in existing_indexes:
                op.create_index('idx_bonds_status', 'bonds', ['status'])
                
            if 'idx_bonds_type' not in existing_indexes:
                op.create_index('idx_bonds_type', 'bonds', ['type'])
                
            if 'idx_bonds_status_type' not in existing_indexes:
                op.create_index('idx_bonds_status_type', 'bonds', ['status', 'type'])
                
            # Add check constraints
            try:
                op.create_check_constraint('check_valid_status', 'bonds', 
                                         "status IN ('available', 'purchased', 'reserved')")
            except:
                pass  # Constraint might already exist
                
            try:
                op.create_check_constraint('check_positive_retail_price', 'bonds', 'retail_price > 0')
            except:
                pass  # Constraint might already exist
                
        except Exception as e:
            print(f"Error updating bonds: {e}")
    
    # Add timestamp columns to transactions table
    if 'transactions' in inspector.get_table_names():
        existing_columns = [col['name'] for col in inspector.get_columns('transactions')]
        
        try:
            if 'created_at' not in existing_columns:
                op.add_column('transactions', 
                    sa.Column('created_at', sa.DateTime(timezone=True), 
                             server_default=sa.text('now()'), nullable=False))
                
            if 'updated_at' not in existing_columns:
                op.add_column('transactions', 
                    sa.Column('updated_at', sa.DateTime(timezone=True), 
                             server_default=sa.text('now()'), nullable=False))
                
            # Add indexes for transactions
            existing_indexes = [idx['name'] for idx in inspector.get_indexes('transactions')]
            
            if 'idx_transactions_paypal_id' not in existing_indexes:
                op.create_index('idx_transactions_paypal_id', 'transactions', ['paypal_transaction_id'])
                
            if 'idx_transactions_item_id' not in existing_indexes:
                op.create_index('idx_transactions_item_id', 'transactions', ['item_id'])
                
            if 'idx_transactions_donor_id' not in existing_indexes:
                op.create_index('idx_transactions_donor_id', 'transactions', ['donor_id'])
                
            if 'idx_transactions_timestamp' not in existing_indexes:
                op.create_index('idx_transactions_timestamp', 'transactions', ['timestamp'])
                
            if 'idx_transactions_status' not in existing_indexes:
                op.create_index('idx_transactions_status', 'transactions', ['payment_status'])
                
            if 'idx_transactions_email' not in existing_indexes:
                op.create_index('idx_transactions_email', 'transactions', ['donor_email'])
                
            if 'idx_transactions_timestamp_status' not in existing_indexes:
                op.create_index('idx_transactions_timestamp_status', 'transactions', ['timestamp', 'payment_status'])
                
            if 'idx_transactions_donor_timestamp' not in existing_indexes:
                op.create_index('idx_transactions_donor_timestamp', 'transactions', ['donor_id', 'timestamp'])
                
            # Add check constraints
            try:
                op.create_check_constraint('check_valid_payment_status', 'transactions', 
                                         "payment_status IN ('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED')")
            except:
                pass  # Constraint might already exist
                
            try:
                op.create_check_constraint('check_positive_transaction_fee', 'transactions', 'fee > 0')
            except:
                pass  # Constraint might already exist
                
        except Exception as e:
            print(f"Error updating transactions: {e}")


def downgrade():
    """Remove timestamp columns and indexes"""
    
    # Remove indexes and constraints for transactions
    try:
        op.drop_index('idx_transactions_donor_timestamp', 'transactions')
        op.drop_index('idx_transactions_timestamp_status', 'transactions')
        op.drop_index('idx_transactions_email', 'transactions')
        op.drop_index('idx_transactions_status', 'transactions')
        op.drop_index('idx_transactions_timestamp', 'transactions')
        op.drop_index('idx_transactions_donor_id', 'transactions')
        op.drop_index('idx_transactions_item_id', 'transactions')
        op.drop_index('idx_transactions_paypal_id', 'transactions')
        op.drop_constraint('check_positive_transaction_fee', 'transactions')
        op.drop_constraint('check_valid_payment_status', 'transactions')
        op.drop_column('transactions', 'updated_at')
        op.drop_column('transactions', 'created_at')
    except Exception as e:
        print(f"Error removing transactions updates: {e}")
    
    # Remove indexes and constraints for bonds
    try:
        op.drop_index('idx_bonds_status_type', 'bonds')
        op.drop_index('idx_bonds_type', 'bonds')
        op.drop_index('idx_bonds_status', 'bonds')
        op.drop_index('idx_bonds_issue_date', 'bonds')
        op.drop_constraint('check_positive_retail_price', 'bonds')
        op.drop_constraint('check_valid_status', 'bonds')
        op.drop_column('bonds', 'updated_at')
        op.drop_column('bonds', 'created_at')
    except Exception as e:
        print(f"Error removing bonds updates: {e}")
    
    # Remove indexes for donors
    try:
        op.drop_index('idx_donors_email', 'donors')
        op.drop_index('idx_donors_name', 'donors')
        op.drop_column('donors', 'updated_at')
        op.drop_column('donors', 'created_at')
    except Exception as e:
        print(f"Error removing donors updates: {e}")
    
    # Remove indexes and constraints for historical_records
    try:
        op.drop_index('idx_historical_records_fee', 'historical_records')
        op.drop_index('idx_historical_records_adopted_name', 'historical_records')
        op.drop_index('idx_historical_records_adopted', 'historical_records')
        op.drop_index('idx_historical_records_name', 'historical_records')
        op.drop_constraint('check_name_not_empty', 'historical_records')
        op.drop_constraint('check_positive_fee', 'historical_records')
        op.drop_column('historical_records', 'updated_at')
        op.drop_column('historical_records', 'created_at')
    except Exception as e:
        print(f"Error removing historical_records updates: {e}")
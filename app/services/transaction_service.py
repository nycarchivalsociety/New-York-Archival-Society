# app/services/transaction_service.py

import logging
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload

from app.db.db import db
from app.db.models import Transaction, Donor, HistoricalRecord, Bond, DonorItem
from app.services.paypal_service import paypal_service, PayPalAPIError

logger = logging.getLogger(__name__)

class TransactionError(Exception):
    """Custom exception for transaction-related errors"""
    pass

class TransactionService:
    """Enhanced service class for handling transaction operations with optimizations"""
    
    @staticmethod
    def create_transaction_with_optimized_rollback(
        order_id: str,
        item_id: str,
        fee: float,
        payer_data: Dict[str, Any],
        is_pickup: bool = False,
        batch_mode: bool = False
    ) -> Tuple[Transaction, bool]:
        """
        Create transaction with proper rollback handling
        
        Args:
            order_id: PayPal order ID
            item_id: Item being purchased
            fee: Transaction amount
            payer_data: PayPal payer information
            is_pickup: Whether item is for pickup
            
        Returns:
            Tuple of (Transaction, is_new_transaction)
            
        Raises:
            TransactionError: If transaction creation fails
        """
        try:
            # Check for existing transaction
            existing_transaction = Transaction.query.filter_by(
                paypal_transaction_id=order_id
            ).first()
            
            if existing_transaction:
                logger.info(f"Transaction already exists for order {order_id}")
                return existing_transaction, False
            
            # Extract payer information
            payer_email = payer_data.get('email_address')
            payer_name = TransactionService._extract_payer_name(payer_data)
            phone = TransactionService._extract_phone(payer_data)
            address = TransactionService._extract_address(payer_data)
            
            # Get or create donor
            donor = TransactionService._get_or_create_donor(
                payer_email, payer_name, phone, address
            )
            
            # Flush to ensure donor has an ID
            db.session.flush()
            
            # Create transaction
            transaction = Transaction(
                paypal_transaction_id=order_id,
                item_id=str(item_id),
                donor_id=donor.donor_id,
                fee=fee,
                payment_status='COMPLETED',
                payment_method='PayPal',
                donor_email=payer_email,
                pickup=is_pickup,
                timestamp=datetime.now()
            )
            
            db.session.add(transaction)
            
            # Create DonorItem for historical records
            if Transaction.is_uuid(item_id):
                donor_item = DonorItem(
                    donor_id=donor.donor_id,
                    item_id=item_id,
                    fee=fee
                )
                db.session.add(donor_item)
            
            # Update item status
            TransactionService._update_item_status(item_id)
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Transaction created successfully: {transaction.transaction_id}")
            return transaction, True
                
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error creating transaction: {str(e)}")
            raise TransactionError("Transaction already exists or violates constraints")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error creating transaction: {str(e)}")
            raise TransactionError(f"Database error: {str(e)}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error creating transaction: {str(e)}")
            raise TransactionError(f"Unexpected error: {str(e)}")
    
    @staticmethod
    def _extract_payer_name(payer_data: Dict[str, Any]) -> str:
        """Extract full name from PayPal payer data"""
        name_data = payer_data.get('name', {})
        given_name = name_data.get('given_name', '')
        surname = name_data.get('surname', '')
        return f"{given_name} {surname}".strip() or "Unknown"
    
    @staticmethod
    def _extract_phone(payer_data: Dict[str, Any]) -> Optional[str]:
        """Extract phone number from PayPal payer data"""
        phone_data = payer_data.get('phone', {})
        phone_number = phone_data.get('phone_number', {})
        return phone_number.get('national_number')
    
    @staticmethod
    def _extract_address(payer_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract address from PayPal payer data"""
        # Note: This would need to be adapted based on actual PayPal response structure
        # The address might be in purchase_units.shipping.address
        return {}
    
    @staticmethod
    def _get_or_create_donor(
        email: str,
        name: str,
        phone: Optional[str],
        address: Dict[str, str]
    ) -> Donor:
        """Get existing donor or create new one"""
        donor = None
        
        if email:
            donor = Donor.query.filter_by(donor_email=email).first()
        
        if not donor:
            donor = Donor(
                donor_name=name,
                donor_email=email,
                phone=phone,
                shipping_street=address.get('address_line_1'),
                shipping_apartment=address.get('address_line_2'),
                shipping_city=address.get('admin_area_2'),
                shipping_state=address.get('admin_area_1'),
                shipping_zip_code=address.get('postal_code')
            )
            db.session.add(donor)
        else:
            # Update existing donor information if provided
            if address:
                donor.shipping_street = address.get('address_line_1', donor.shipping_street)
                donor.shipping_apartment = address.get('address_line_2', donor.shipping_apartment)
                donor.shipping_city = address.get('admin_area_2', donor.shipping_city)
                donor.shipping_state = address.get('admin_area_1', donor.shipping_state)
                donor.shipping_zip_code = address.get('postal_code', donor.shipping_zip_code)
            
            if phone:
                donor.phone = phone
        
        return donor
    
    @staticmethod
    def _update_item_status(item_id: str) -> None:
        """Update item status based on item type"""
        if Transaction.is_uuid(item_id):
            # Historical record
            item = HistoricalRecord.query.get(item_id)
            if item:
                item.adopted = True
            else:
                raise TransactionError(f"Historical record {item_id} not found")
        else:
            # Bond
            item = Bond.query.get(item_id)
            if item:
                item.status = 'purchased'
            else:
                raise TransactionError(f"Bond {item_id} not found")
    
    @staticmethod
    def get_transaction_by_paypal_id(paypal_transaction_id: str) -> Optional[Transaction]:
        """Get transaction by PayPal transaction ID"""
        return Transaction.query.filter_by(
            paypal_transaction_id=paypal_transaction_id
        ).first()
    
    @staticmethod
    def get_donor_transactions(donor_id: str, limit: int = 10) -> list:
        """Get transactions for a specific donor"""
        return Transaction.query\
            .filter_by(donor_id=donor_id)\
            .order_by(Transaction.timestamp.desc())\
            .limit(limit)\
            .all()

    @staticmethod
    def bulk_create_transactions(
        transaction_data: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Tuple[List[Transaction], List[str]]:
        """
        Bulk create transactions for improved performance
        
        Args:
            transaction_data: List of transaction dictionaries
            batch_size: Number of transactions to process per batch
            
        Returns:
            Tuple of (created_transactions, failed_order_ids)
        """
        created_transactions = []
        failed_order_ids = []
        
        # Process in batches for memory efficiency
        for i in range(0, len(transaction_data), batch_size):
            batch = transaction_data[i:i + batch_size]
            
            try:
                with db.session.begin():
                    batch_transactions = []
                    
                    for data in batch:
                        try:
                            # Check for existing transaction
                            existing = Transaction.query.filter_by(
                                paypal_transaction_id=data['order_id']
                            ).first()
                            
                            if existing:
                                logger.info(f"Transaction exists: {data['order_id']}")
                                created_transactions.append(existing)
                                continue
                            
                            # Extract and validate data
                            payer_data = data.get('payer_data', {})
                            payer_email = payer_data.get('email_address')
                            payer_name = TransactionService._extract_payer_name(payer_data)
                            
                            # Get or create donor (batch optimized)
                            donor = TransactionService._get_or_create_donor_batch(
                                payer_email, payer_name, 
                                data.get('phone'), data.get('address', {})
                            )
                            
                            # Create transaction object
                            transaction = Transaction(
                                paypal_transaction_id=data['order_id'],
                                item_id=str(data['item_id']),
                                donor_id=donor.donor_id,
                                fee=data['fee'],
                                payment_status='COMPLETED',
                                payment_method='PayPal',
                                donor_email=payer_email,
                                pickup=data.get('is_pickup', False),
                                timestamp=datetime.now()
                            )
                            
                            batch_transactions.append(transaction)
                            
                        except Exception as e:
                            logger.error(f"Failed to prepare transaction {data.get('order_id')}: {str(e)}")
                            failed_order_ids.append(data.get('order_id'))
                    
                    # Bulk insert transactions
                    if batch_transactions:
                        db.session.add_all(batch_transactions)
                        db.session.flush()
                        
                        # Bulk create DonorItems and update item statuses
                        TransactionService._bulk_update_items([t.item_id for t in batch_transactions])
                        
                        created_transactions.extend(batch_transactions)
                        
                        logger.info(f"Bulk created {len(batch_transactions)} transactions")
                        
            except Exception as e:
                logger.error(f"Batch transaction creation failed: {str(e)}")
                # Add all order_ids from this batch to failed list
                failed_order_ids.extend([data.get('order_id') for data in batch])
        
        return created_transactions, failed_order_ids
    
    @staticmethod
    def _get_or_create_donor_batch(
        email: str,
        name: str,
        phone: Optional[str],
        address: Dict[str, str]
    ) -> Donor:
        """Optimized donor creation for batch operations"""
        # Use get_or_create pattern with minimal queries
        if email:
            donor = db.session.query(Donor).filter_by(donor_email=email).first()
            if donor:
                return donor
        
        # Create new donor
        donor = Donor(
            donor_name=name,
            donor_email=email,
            phone=phone,
            shipping_street=address.get('address_line_1'),
            shipping_apartment=address.get('address_line_2'),
            shipping_city=address.get('admin_area_2'),
            shipping_state=address.get('admin_area_1'),
            shipping_zip_code=address.get('postal_code')
        )
        
        db.session.add(donor)
        db.session.flush()  # Get ID without committing
        return donor
    
    @staticmethod
    def _bulk_update_items(item_ids: List[str]) -> None:
        """Bulk update item statuses for performance"""
        if not item_ids:
            return
        
        # Separate UUIDs (historical records) from strings (bonds)
        uuid_items = [id for id in item_ids if Transaction.is_uuid(id)]
        bond_items = [id for id in item_ids if not Transaction.is_uuid(id)]
        
        # Bulk update historical records
        if uuid_items:
            db.session.execute(
                text("""
                    UPDATE historical_records 
                    SET adopted = true, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ANY(:item_ids)
                """),
                {'item_ids': uuid_items}
            )
            
            # Bulk create DonorItems
            donor_items = []
            for item_id in uuid_items:
                # This would need donor_id - simplified for example
                donor_item = DonorItem(
                    item_id=item_id,
                    # donor_id would be provided in real implementation
                    fee=0  # Would be actual fee
                )
                donor_items.append(donor_item)
            
            if donor_items:
                db.session.add_all(donor_items)
        
        # Bulk update bonds
        if bond_items:
            db.session.execute(
                text("""
                    UPDATE bonds 
                    SET status = 'purchased', updated_at = CURRENT_TIMESTAMP 
                    WHERE bond_id = ANY(:item_ids)
                """),
                {'item_ids': bond_items}
            )
    
    @staticmethod
    def get_transaction_analytics(
        start_date: datetime = None,
        end_date: datetime = None,
        group_by: str = 'day'
    ) -> Dict[str, Any]:
        """
        Get transaction analytics with optimized aggregation queries
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            group_by: Grouping period ('day', 'week', 'month')
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        # Base query with date filtering
        base_query = db.session.query(Transaction)\
            .filter(Transaction.timestamp.between(start_date, end_date))\
            .filter(Transaction.payment_status == 'COMPLETED')
        
        # Revenue analytics
        revenue_stats = db.session.query(
            func.count(Transaction.transaction_id).label('total_transactions'),
            func.sum(Transaction.fee).label('total_revenue'),
            func.avg(Transaction.fee).label('average_transaction'),
            func.min(Transaction.fee).label('min_transaction'),
            func.max(Transaction.fee).label('max_transaction')
        ).filter(
            Transaction.timestamp.between(start_date, end_date),
            Transaction.payment_status == 'COMPLETED'
        ).first()
        
        # Time-based grouping
        if group_by == 'day':
            time_expr = func.date(Transaction.timestamp)
        elif group_by == 'week':
            time_expr = func.date_trunc('week', Transaction.timestamp)
        else:  # month
            time_expr = func.date_trunc('month', Transaction.timestamp)
        
        time_series = db.session.query(
            time_expr.label('period'),
            func.count(Transaction.transaction_id).label('transactions'),
            func.sum(Transaction.fee).label('revenue')
        ).filter(
            Transaction.timestamp.between(start_date, end_date),
            Transaction.payment_status == 'COMPLETED'
        ).group_by(time_expr)\
        .order_by(time_expr)\
        .all()
        
        # Item type analysis
        item_type_stats = db.session.query(
            func.case(
                (func.char_length(Transaction.item_id) == 36, 'historical_record'),
                else_='bond'
            ).label('item_type'),
            func.count(Transaction.transaction_id).label('count'),
            func.sum(Transaction.fee).label('revenue')
        ).filter(
            Transaction.timestamp.between(start_date, end_date),
            Transaction.payment_status == 'COMPLETED'
        ).group_by('item_type').all()
        
        return {
            'summary': {
                'total_transactions': revenue_stats.total_transactions or 0,
                'total_revenue': float(revenue_stats.total_revenue or 0),
                'average_transaction': float(revenue_stats.average_transaction or 0),
                'min_transaction': float(revenue_stats.min_transaction or 0),
                'max_transaction': float(revenue_stats.max_transaction or 0)
            },
            'time_series': [
                {
                    'period': period.isoformat() if hasattr(period, 'isoformat') else str(period),
                    'transactions': transactions,
                    'revenue': float(revenue or 0)
                }
                for period, transactions, revenue in time_series
            ],
            'item_types': [
                {
                    'type': item_type,
                    'count': count,
                    'revenue': float(revenue or 0)
                }
                for item_type, count, revenue in item_type_stats
            ]
        }

    # Backward compatibility method
    @staticmethod
    def create_transaction_with_rollback(*args, **kwargs):
        """Backward compatibility wrapper"""
        return TransactionService.create_transaction_with_optimized_rollback(*args, **kwargs)


# Global service instance
transaction_service = TransactionService()
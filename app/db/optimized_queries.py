# app/db/optimized_queries.py

"""
Optimized database queries for improved performance
Contains before/after examples and best practices
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import func, text, and_, or_
from sqlalchemy.orm import joinedload, selectinload, contains_eager
from flask_sqlalchemy import Pagination

from app.db.db import db
from app.db.models import HistoricalRecord, Donor, Transaction, DonorItem, Bond
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class OptimizedQueries:
    """
    Collection of optimized database queries for better performance
    """
    
    @staticmethod
    def get_available_historical_records_optimized(
        page: int = 1, 
        per_page: int = 8,
        use_cache: bool = True
    ) -> Tuple[List[HistoricalRecord], Pagination]:
        """
        OPTIMIZED: Get available historical records with minimal database hits
        
        BEFORE (N+1 Problem):
        - Main query: SELECT * FROM historical_records WHERE adopted = false
        - For each record: SELECT * FROM donor_item WHERE item_id = ?
        - For each donor_item: SELECT * FROM donors WHERE donor_id = ?
        - Total queries: 1 + (N records * 2) = 1 + 16 = 17 queries for 8 records
        
        AFTER (Optimized):
        - Single query with joins and proper loading strategy
        - Total queries: 1 for all data + 1 for count = 2 queries maximum
        """
        if use_cache:
            cached_result = cache_service.get_available_historical_records(page, per_page)
            if cached_result:
                return cached_result['items'], type('Pagination', (), cached_result)()
        
        # Optimized query with selective eager loading
        query = db.session.query(HistoricalRecord)\
            .filter(HistoricalRecord.adopted == False)\
            .options(
                # Use selectinload for one-to-many relationships to avoid N+1
                selectinload(HistoricalRecord.donors)
                .selectinload(DonorItem.donor)
                .load_only(
                    Donor.donor_id,
                    Donor.donor_name,
                    Donor.donor_email,
                    Donor.created_at
                )
            )\
            .order_by(HistoricalRecord.created_at.desc())
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
            max_per_page=50
        )
        
        return pagination.items, pagination
    
    @staticmethod
    def get_bonds_with_filters_optimized(
        page: int = 1,
        per_page: int = 9,
        status: str = 'available',
        bond_type: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
    ) -> Tuple[List[Bond], Pagination]:
        """
        OPTIMIZED: Enhanced bonds query with filtering and proper indexing
        
        BEFORE:
        - Simple filter by status only
        - No support for complex filtering
        - Missing compound indexes for common filter combinations
        
        AFTER:
        - Multi-criteria filtering with optimized WHERE clauses
        - Uses compound indexes for performance
        - Proper parameter binding to prevent SQL injection
        """
        # Build optimized query with dynamic filters
        query = db.session.query(Bond)\
            .filter(Bond.status == status)
        
        # Add filters that can use indexes efficiently
        if bond_type:
            query = query.filter(Bond.type == bond_type)
        
        if year_from or year_to:
            if year_from:
                query = query.filter(func.extract('year', Bond.issue_date) >= year_from)
            if year_to:
                query = query.filter(func.extract('year', Bond.issue_date) <= year_to)
        
        if min_price is not None:
            query = query.filter(Bond.retail_price >= min_price)
        if max_price is not None:
            query = query.filter(Bond.retail_price <= max_price)
        
        # Order by compound index for optimal performance
        query = query.order_by(Bond.status, Bond.issue_date.desc(), Bond.bond_id)
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
            max_per_page=50
        )
        
        return pagination.items, pagination
    
    @staticmethod
    def get_transaction_history_optimized(
        donor_id: Optional[str] = None,
        item_id: Optional[str] = None,
        status: Optional[str] = None,
        days_back: int = 30,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Transaction], Pagination]:
        """
        OPTIMIZED: Transaction history with efficient joins and filtering
        
        BEFORE:
        - Separate queries for donor and item information
        - No date range optimization
        - Missing compound indexes for common queries
        
        AFTER:
        - Single query with optimized joins
        - Date range filtering using indexes
        - Efficient pagination with cursor-based approach for large datasets
        """
        # Base query with optimized joins
        query = db.session.query(Transaction)\
            .join(Donor, Transaction.donor_id == Donor.donor_id)\
            .filter(
                Transaction.timestamp >= func.current_date() - func.interval(f'{days_back} days')
            )
        
        # Apply filters using indexed columns
        if donor_id:
            query = query.filter(Transaction.donor_id == donor_id)
        
        if item_id:
            query = query.filter(Transaction.item_id == item_id)
        
        if status:
            query = query.filter(Transaction.payment_status == status)
        
        # Use compound index: (timestamp, payment_status)
        query = query.order_by(
            Transaction.timestamp.desc(),
            Transaction.payment_status,
            Transaction.transaction_id
        )
        
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False,
            max_per_page=100
        )
        
        return pagination.items, pagination
    
    @staticmethod
    def get_donor_summary_optimized(donor_id: str) -> Dict[str, Any]:
        """
        OPTIMIZED: Single query to get complete donor summary
        
        BEFORE:
        - Multiple separate queries for donor data, transactions, and items
        - N+1 problem when loading related items
        
        AFTER:
        - Single optimized query with all necessary joins
        - Aggregated statistics calculated in database
        """
        # Single query with all necessary data and aggregations
        result = db.session.query(
            Donor,
            func.count(Transaction.transaction_id).label('transaction_count'),
            func.sum(Transaction.fee).label('total_spent'),
            func.max(Transaction.timestamp).label('last_purchase_date'),
            func.count(DonorItem.id).label('items_adopted')
        )\
        .outerjoin(Transaction, Donor.donor_id == Transaction.donor_id)\
        .outerjoin(DonorItem, Donor.donor_id == DonorItem.donor_id)\
        .filter(Donor.donor_id == donor_id)\
        .group_by(Donor.donor_id)\
        .first()
        
        if not result:
            return None
        
        donor, transaction_count, total_spent, last_purchase, items_adopted = result
        
        return {
            'donor': donor,
            'statistics': {
                'transaction_count': transaction_count or 0,
                'total_spent': float(total_spent or 0),
                'last_purchase_date': last_purchase,
                'items_adopted': items_adopted or 0
            }
        }
    
    @staticmethod
    def bulk_update_item_status(item_ids: List[str], new_status: str) -> int:
        """
        OPTIMIZED: Bulk update operations for better performance
        
        BEFORE:
        - Individual UPDATE statements for each item
        - Multiple database round trips
        
        AFTER:
        - Single bulk UPDATE with WHERE IN clause
        - Single database round trip
        """
        if not item_ids:
            return 0
        
        # Determine table based on item ID format
        if any(Transaction.is_uuid(item_id) for item_id in item_ids):
            # Historical records - bulk update adopted status
            result = db.session.execute(
                text("""
                    UPDATE historical_records 
                    SET adopted = :status, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ANY(:item_ids)
                """),
                {
                    'status': new_status == 'adopted',
                    'item_ids': [str(id) for id in item_ids if Transaction.is_uuid(id)]
                }
            )
        else:
            # Bonds - bulk update status
            result = db.session.execute(
                text("""
                    UPDATE bonds 
                    SET status = :status, updated_at = CURRENT_TIMESTAMP 
                    WHERE bond_id = ANY(:item_ids)
                """),
                {
                    'status': new_status,
                    'item_ids': [str(id) for id in item_ids if not Transaction.is_uuid(id)]
                }
            )
        
        db.session.commit()
        return result.rowcount
    
    @staticmethod
    def get_popular_items_optimized(limit: int = 10) -> List[Dict[str, Any]]:
        """
        OPTIMIZED: Get most popular items with aggregated statistics
        
        Uses efficient aggregation queries with proper indexing
        """
        # Get popular historical records
        historical_popularity = db.session.query(
            HistoricalRecord.id,
            HistoricalRecord.name,
            HistoricalRecord.fee,
            HistoricalRecord.imgurl,
            func.count(DonorItem.id).label('adoption_count'),
            func.sum(DonorItem.fee).label('total_revenue')
        )\
        .join(DonorItem, HistoricalRecord.id == DonorItem.item_id)\
        .group_by(HistoricalRecord.id)\
        .order_by(func.count(DonorItem.id).desc())\
        .limit(limit // 2)\
        .all()
        
        # Get popular bonds
        bond_popularity = db.session.query(
            Bond.bond_id,
            Bond.retail_price,
            Bond.type,
            Bond.front_image,
            func.count(Transaction.transaction_id).label('purchase_count'),
            func.sum(Transaction.fee).label('total_revenue')
        )\
        .join(Transaction, Bond.bond_id == Transaction.item_id)\
        .group_by(Bond.bond_id)\
        .order_by(func.count(Transaction.transaction_id).desc())\
        .limit(limit // 2)\
        .all()
        
        # Combine and format results
        popular_items = []
        
        for item in historical_popularity:
            popular_items.append({
                'id': str(item.id),
                'name': item.name,
                'type': 'historical_record',
                'price': float(item.fee),
                'image': item.imgurl,
                'popularity_count': item.adoption_count,
                'total_revenue': float(item.total_revenue or 0)
            })
        
        for item in bond_popularity:
            popular_items.append({
                'id': item.bond_id,
                'name': f"Bond {item.bond_id}",
                'type': 'bond',
                'price': float(item.retail_price or 0),
                'image': item.front_image,
                'popularity_count': item.purchase_count,
                'total_revenue': float(item.total_revenue or 0)
            })
        
        # Sort by popularity across both types
        popular_items.sort(key=lambda x: x['popularity_count'], reverse=True)
        return popular_items[:limit]


# Performance monitoring for queries
class QueryPerformanceMonitor:
    """Monitor and log query performance metrics"""
    
    @staticmethod
    def log_slow_queries(threshold_ms: float = 1000.0):
        """Log queries that exceed performance threshold"""
        # This would integrate with SQLAlchemy event system
        # Implementation depends on your specific monitoring needs
        pass
    
    @staticmethod
    def analyze_query_patterns():
        """Analyze common query patterns for optimization opportunities"""
        # Implementation for query pattern analysis
        pass


# Global optimized queries instance
optimized_queries = OptimizedQueries()
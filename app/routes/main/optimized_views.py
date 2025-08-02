# app/routes/main/optimized_views.py

"""
Optimized views using enhanced database performance techniques
Demonstrates the implementation of all optimization strategies
"""

from . import main
from flask import render_template, jsonify, request, current_app
import logging
from app.db.db import db
from app.db.models import HistoricalRecord, Donor, Transaction, DonorItem, Bond
from app.db.optimized_queries import optimized_queries
from app.services.paypal_service import paypal_service, PayPalAPIError
from app.services.transaction_service import transaction_service, TransactionError
from app.services.cache_service import advanced_cache_service
from app.utils.validators import (
    validate_paypal_order_data, validate_capture_order_data, 
    validate_pagination_params, require_json, validate_request_size,
    validate_uuid, ValidationError
)
from app.utils.db_monitoring import query_performance_monitor, query_analysis_context
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import os
from datetime import datetime
from functools import wraps

# Configure logging for this module
logger = logging.getLogger(__name__)

# Performance-optimized parameters
PER_PAGE_OPTIMIZED = 20
MAX_PER_PAGE_OPTIMIZED = 50
CACHE_TIMEOUT_HOT = 300  # 5 minutes for frequently accessed data
CACHE_TIMEOUT_WARM = 900  # 15 minutes for regularly accessed data


def handle_errors_optimized(f):
    """Enhanced error handling decorator with performance monitoring"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            with query_analysis_context(f.__name__):
                return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {f.__name__}: {str(e)} from {request.remote_addr}")
            return jsonify({'error': str(e)}), 400
        except PayPalAPIError as e:
            logger.error(f"PayPal API error in {f.__name__}: {str(e)}")
            return jsonify({'error': 'Payment processing error'}), 500
        except TransactionError as e:
            logger.error(f"Transaction error in {f.__name__}: {str(e)}")
            return jsonify({'error': 'Transaction processing error'}), 500
        except SQLAlchemyError as e:
            logger.error(f"Database error in {f.__name__}: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Database error occurred'}), 500
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({'error': 'An unexpected error occurred'}), 500
    return decorated_function


@main.route('/optimized/adopt-new-yorks-past')
@handle_errors_optimized
@query_performance_monitor(threshold_seconds=0.5)
@advanced_cache_service.smart_cache(tier='warm', key_prefix='historical_records')
def optimized_new_yorks_past():
    """
    OPTIMIZED: Display available and adopted historical records
    
    Performance Improvements:
    - Uses selectinload to avoid N+1 queries
    - Implements smart caching with multiple tiers
    - Applies compound indexes for sorting
    - Uses covering indexes to reduce data fetching
    """
    # Validate pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 8, type=int)
    
    pagination_params = validate_pagination_params(page, per_page, max_per_page=MAX_PER_PAGE_OPTIMIZED)
    page = pagination_params['page']
    per_page = pagination_params['per_page']
    
    # Extract filters for more sophisticated caching
    filters = {
        'min_fee': request.args.get('min_fee', type=float),
        'max_fee': request.args.get('max_fee', type=float),
        'search': request.args.get('search', '').strip()
    }
    
    # Use optimized query with advanced caching
    available_items, pagination = optimized_queries.get_available_historical_records_optimized(
        page=page, 
        per_page=per_page,
        use_cache=True
    )
    
    # Optimized query for adopted items with limit to prevent performance issues
    adopted_items = optimized_queries.get_available_historical_records_optimized(
        page=1,
        per_page=20,
        use_cache=True
    )[0]  # Just get items, not pagination
    
    # Filter to only adopted items
    adopted_items = [item for item in adopted_items if getattr(item, 'adopted', False)]
    
    logger.info(f"Optimized historical records page {page} served with {len(available_items)} items")
    
    return render_template(
        'Adopt_New_Yorks_Past/adopt_new_yorks_past.html',
        pagination=pagination,
        adopted_items=adopted_items
    )


@main.route('/optimized/bonds')
@handle_errors_optimized
@query_performance_monitor(threshold_seconds=0.3)
@advanced_cache_service.smart_cache(tier='warm', key_prefix='bonds')
def optimized_get_bonds():
    """
    OPTIMIZED: Display available bonds with advanced filtering and caching
    
    Performance Improvements:
    - Multi-criteria filtering with optimized WHERE clauses
    - Uses compound indexes for performance
    - Advanced caching with filter-aware keys
    - Proper parameter binding to prevent SQL injection
    """
    # Validate pagination parameters
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = request.args.get('per_page', 9, type=int)
    
    pagination_params = validate_pagination_params(page, per_page, max_per_page=MAX_PER_PAGE_OPTIMIZED)
    page = pagination_params['page']
    per_page = pagination_params['per_page']
    
    # Extract and validate filters
    filters = {
        'status': request.args.get('status', 'available'),
        'bond_type': request.args.get('type'),
        'year_from': request.args.get('year_from', type=int),
        'year_to': request.args.get('year_to', type=int),
        'min_price': request.args.get('min_price', type=float),
        'max_price': request.args.get('max_price', type=float)
    }
    
    # Remove None values for cleaner caching
    filters = {k: v for k, v in filters.items() if v is not None}
    
    # Use optimized query with filtering
    bonds, pagination = optimized_queries.get_bonds_with_filters_optimized(
        page=page,
        per_page=per_page,
        **filters
    )
    
    logger.info(f"Optimized bonds page {page} served with {len(bonds)} bonds")
    
    return render_template(
        'Bonds/bonds_list.html',
        bonds=bonds,
        pagination=pagination,
        current_filters=filters
    )


@main.route('/optimized/transaction-history')
@handle_errors_optimized
@query_performance_monitor(threshold_seconds=1.0)
@advanced_cache_service.smart_cache(tier='cold', key_prefix='transaction_history')
def optimized_transaction_history():
    """
    OPTIMIZED: Transaction history with efficient joins and filtering
    
    Performance Improvements:
    - Single query with optimized joins
    - Date range filtering using indexes
    - Efficient pagination with cursor-based approach
    - Smart caching for frequently accessed data
    """
    # Validate pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    pagination_params = validate_pagination_params(page, per_page, max_per_page=100)
    page = pagination_params['page']
    per_page = pagination_params['per_page']
    
    # Extract filters
    filters = {
        'donor_id': request.args.get('donor_id'),
        'item_id': request.args.get('item_id'),
        'status': request.args.get('status'),
        'days_back': request.args.get('days_back', 30, type=int)
    }
    
    # Use optimized transaction query
    transactions, pagination = optimized_queries.get_transaction_history_optimized(
        page=page,
        per_page=per_page,
        **{k: v for k, v in filters.items() if v is not None}
    )
    
    return jsonify({
        'transactions': [
            {
                'id': str(t.transaction_id),
                'paypal_id': t.paypal_transaction_id,
                'item_id': t.item_id,
                'fee': float(t.fee),
                'status': t.payment_status,
                'timestamp': t.timestamp.isoformat(),
                'donor_email': t.donor_email
            }
            for t in transactions
        ],
        'pagination': {
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })


@main.route('/optimized/donor/<donor_id>/summary')
@handle_errors_optimized
@query_performance_monitor(threshold_seconds=0.5)
@advanced_cache_service.smart_cache(tier='warm', key_prefix='donor_summary')
def optimized_donor_summary(donor_id):
    """
    OPTIMIZED: Complete donor summary with single query
    
    Performance Improvements:
    - Single optimized query with all necessary joins
    - Aggregated statistics calculated in database
    - Smart caching for donor data
    """
    # Validate donor ID
    if not validate_uuid(donor_id):
        return jsonify({'error': 'Invalid donor ID'}), 400
    
    # Use optimized donor summary query
    summary = optimized_queries.get_donor_summary_optimized(donor_id)
    
    if not summary:
        return jsonify({'error': 'Donor not found'}), 404
    
    return jsonify({
        'donor': {
            'id': str(summary['donor'].donor_id),
            'name': summary['donor'].donor_name,
            'email': summary['donor'].donor_email,
            'phone': summary['donor'].phone,
            'created_at': summary['donor'].created_at.isoformat()
        },
        'statistics': summary['statistics']
    })


@main.route('/optimized/popular-items')
@handle_errors_optimized
@query_performance_monitor(threshold_seconds=1.0)
@advanced_cache_service.smart_cache(tier='frozen', key_prefix='popular_items')
def optimized_popular_items():
    """
    OPTIMIZED: Get most popular items with aggregated statistics
    
    Performance Improvements:
    - Efficient aggregation queries with proper indexing
    - Long-term caching for relatively stable data
    - Combined results from multiple item types
    """
    limit = request.args.get('limit', 10, type=int)
    limit = min(limit, 50)  # Cap at 50 for performance
    
    popular_items = optimized_queries.get_popular_items_optimized(limit=limit)
    
    return jsonify({
        'popular_items': popular_items,
        'generated_at': datetime.now().isoformat(),
        'cache_info': 'Results cached for optimal performance'
    })


@main.route('/optimized/analytics/transactions')
@handle_errors_optimized
@query_performance_monitor(threshold_seconds=2.0)
@advanced_cache_service.smart_cache(tier='cold', key_prefix='transaction_analytics')
def optimized_transaction_analytics():
    """
    OPTIMIZED: Transaction analytics with efficient aggregation
    
    Performance Improvements:
    - Database-level aggregations for better performance
    - Time-based grouping with optimized date functions
    - Caching for expensive analytical queries
    """
    # Parse date parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    group_by = request.args.get('group_by', 'day')
    
    # Convert string dates to datetime objects
    try:
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO format.'}), 400
    
    # Get analytics data
    analytics = transaction_service.get_transaction_analytics(
        start_date=start_date,
        end_date=end_date,
        group_by=group_by
    )
    
    return jsonify(analytics)


@main.route('/optimized/bulk-update-items', methods=['POST'])
@require_json
@validate_request_size()
@handle_errors_optimized
@query_performance_monitor(threshold_seconds=5.0)
def optimized_bulk_update_items():
    """
    OPTIMIZED: Bulk update operations for better performance
    
    Performance Improvements:
    - Single bulk UPDATE with WHERE IN clause
    - Single database round trip
    - Proper transaction handling
    """
    data = request.get_json()
    
    item_ids = data.get('item_ids', [])
    new_status = data.get('status')
    
    if not item_ids or not new_status:
        return jsonify({'error': 'item_ids and status are required'}), 400
    
    if len(item_ids) > 1000:  # Prevent excessive bulk operations
        return jsonify({'error': 'Too many items for bulk update (max 1000)'}), 400
    
    # Perform bulk update
    updated_count = optimized_queries.bulk_update_item_status(item_ids, new_status)
    
    # Invalidate relevant caches
    advanced_cache_service.invalidate_pattern('historical_records')
    advanced_cache_service.invalidate_pattern('bonds')
    
    logger.info(f"Bulk updated {updated_count} items to status '{new_status}'")
    
    return jsonify({
        'updated_count': updated_count,
        'message': f'Successfully updated {updated_count} items'
    })


# Performance monitoring endpoints
@main.route('/optimized/performance/stats')
@handle_errors_optimized
def performance_stats():
    """Get current performance statistics"""
    from app.utils.db_monitoring import db_monitor, QueryAnalyzer
    
    stats = {
        'database': {
            'slow_queries': db_monitor.get_slow_queries(5),
            'query_statistics': db_monitor.get_query_statistics(),
            'connection_statistics': db_monitor.get_connection_statistics()
        },
        'cache': advanced_cache_service.get_cache_statistics(),
        'optimization_report': QueryAnalyzer.generate_optimization_report()
    }
    
    return jsonify(stats)


@main.route('/optimized/performance/clear-cache', methods=['POST'])
@handle_errors_optimized
def clear_performance_cache():
    """Clear application cache for testing"""
    try:
        # Clear all cache patterns
        patterns_to_clear = [
            'historical_records',
            'bonds',
            'transaction_history',
            'donor_summary',
            'popular_items',
            'transaction_analytics'
        ]
        
        for pattern in patterns_to_clear:
            advanced_cache_service.invalidate_pattern(pattern)
        
        logger.info("Performance cache cleared")
        return jsonify({'message': 'Cache cleared successfully'})
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        return jsonify({'error': 'Failed to clear cache'}), 500


# Backward compatibility - these routes use the optimized versions
@main.route('/adopt-new-yorks-past-v2')
def new_yorks_past_v2():
    """Backward compatible optimized version"""
    return optimized_new_yorks_past()


@main.route('/bonds-v2')
def get_bonds_v2():
    """Backward compatible optimized version"""
    return optimized_get_bonds()
from . import main
from flask import render_template, jsonify, request, current_app
import logging
from app.db.db import db
from app.db.models import HistoricalRecord, Donor, Transaction, DonorItem, Bond, GeneralProduct
from app.services.paypal_service import paypal_service, PayPalAPIError
from app.services.transaction_service import transaction_service, TransactionError
from app.utils.validators import (
    validate_paypal_order_data, validate_capture_order_data, 
    validate_pagination_params, require_json, validate_request_size,
    validate_uuid, ValidationError
)
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import os
from datetime import datetime
from functools import wraps

# Configure logging for this module
logger = logging.getLogger(__name__)

# Configurable parameters
PER_PAGE = 20
MAX_PER_PAGE = 100
CACHE_TIMEOUT = 300  # 5 minutes

def handle_errors(f):
    """Decorator for consistent error handling"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
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

@main.route('/create-order', methods=['POST'])
@require_json
@validate_request_size()
@handle_errors
def create_order():
    """Create PayPal order with enhanced validation and error handling"""
    data = request.get_json()
    
    # Validate input data
    validated_data = validate_paypal_order_data(data)
    
    # Verify item exists and is available
    item_id = validated_data['item_id']
    item_type = validated_data.get('item_type', 'historical_record')  # Default to historical_record for backward compatibility
    fee = validated_data['fee']
    
    if item_type == 'general_product':
        # General product (UUID-based)
        item = GeneralProduct.query.get(item_id)
        if not item:
            return jsonify({'error': 'General product not found'}), 404
        if item.status != 'available' or item.quantity <= 0:
            return jsonify({'error': 'General product not available'}), 400
        # Fee validation for general products includes handling fee logic handled in frontend
    elif validate_uuid(item_id):
        # Historical record
        item = HistoricalRecord.query.get(item_id)
        if not item:
            return jsonify({'error': 'Historical record not found'}), 404
        if item.adopted:
            return jsonify({'error': 'Historical record already adopted'}), 400
        if float(item.fee) != fee:
            return jsonify({'error': 'Fee mismatch'}), 400
    else:
        # Bond
        item = Bond.query.get(item_id)
        if not item:
            return jsonify({'error': 'Bond not found'}), 404
        if item.status != 'available':
            return jsonify({'error': 'Bond not available'}), 400
        if item.retail_price and float(item.retail_price) != fee:
            return jsonify({'error': 'Fee mismatch'}), 400
    
    # Create PayPal order
    order_data = paypal_service.create_order(item_id, fee)
    
    logger.info(f"PayPal order created: {order_data.get('id')} for item {item_id}")
    return jsonify(order_data)


@main.route('/capture-order/<order_id>', methods=['POST'])
@require_json
@validate_request_size()
@handle_errors
def capture_order(order_id):
    """Capture PayPal order with enhanced security and transaction handling"""
    if not order_id or not isinstance(order_id, str):
        return jsonify({'error': 'Invalid order ID'}), 400
    
    # Validate request data
    data = request.get_json()
    validated_data = validate_capture_order_data(data)
    
    # Check if order already processed
    existing_transaction = transaction_service.get_transaction_by_paypal_id(order_id)
    if existing_transaction:
        logger.info(f"Order {order_id} already processed")
        return jsonify({'message': 'Order already processed'}), 200
    
    # Get order details from PayPal
    order_details = paypal_service.get_order_details(order_id)
    
    # Verify order is completed
    if order_details.get('status') != 'COMPLETED':
        logger.warning(f"Order {order_id} not completed, status: {order_details.get('status')}")
        return jsonify({'error': 'Order not completed'}), 400
    
    # Extract payer information
    payer_data = order_details.get('payer', {})
    purchase_units = order_details.get('purchase_units', [])
    
    # Add shipping address to payer data from purchase units
    if purchase_units:
        shipping = purchase_units[0].get('shipping', {})
        payer_data['shipping_address'] = shipping.get('address', {})
    
    # Debug logging for item_type
    item_type = validated_data.get('item_type', 'historical_record')
    logger.info(f"Capture order debug - item_id: {validated_data['item_id']}, item_type: {item_type}, validated_data: {validated_data}")
    
    # Create transaction using service
    transaction, is_new = transaction_service.create_transaction_with_rollback(
        order_id=order_id,
        item_id=validated_data['item_id'],
        fee=validated_data['fee'],
        payer_data=payer_data,
        is_pickup=validated_data['pickup'],
        item_type=item_type
    )
    
    if is_new:
        logger.info(f"Transaction created successfully: {transaction.transaction_id}")
    else:
        logger.info(f"Existing transaction returned: {transaction.transaction_id}")
    
    return jsonify({'message': 'Success', 'transaction_id': str(transaction.transaction_id)}), 200

@main.route('/')
def index():
    # Render the home page template
    return render_template('Index/index.html')

@main.route('/about')
def about():
    # Render the about page template
    return render_template('About/about.html')

@main.route('/adopt-new-yorks-past')
@handle_errors
def new_yorks_past():
    """Display available and adopted historical records with optimized queries"""
    # Validate pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 8, type=int)
    
    pagination_params = validate_pagination_params(page, per_page, max_per_page=50)
    page = pagination_params['page']
    per_page = pagination_params['per_page']
    
    # Optimized query for available items with proper indexing
    available_query = HistoricalRecord.query\
        .filter_by(adopted=False)\
        .options(joinedload(HistoricalRecord.donors).joinedload(DonorItem.donor))\
        .order_by(HistoricalRecord.created_at.desc())
    
    # Paginate available items
    pagination = available_query.paginate(
        page=page,
        per_page=per_page,
        error_out=False,
        max_per_page=50
    )
    
    # Optimized query for adopted items (limit to recent ones for performance)
    adopted_items = HistoricalRecord.query\
        .filter_by(adopted=True)\
        .options(joinedload(HistoricalRecord.donors).joinedload(DonorItem.donor))\
        .order_by(HistoricalRecord.updated_at.desc())\
        .limit(20)\
        .all()
    
    logger.info(f"Displaying historical records page {page}, {len(pagination.items)} available items")
    
    return render_template(
        'Adopt_New_Yorks_Past/adopt_new_yorks_past.html',
        pagination=pagination,
        adopted_items=adopted_items
    )


@main.route('/adopt-new-yorks-past/item/<item_id>')
@handle_errors
def new_yorks_past_view_item(item_id):
    """Display individual historical record with security validation"""
    # Validate item_id format
    if not validate_uuid(item_id):
        logger.warning(f"Invalid item ID format: {item_id} from {request.remote_addr}")
        return render_template('Error_Pages/404_not_found.html'), 404
    
    # Get item with eager loading for performance
    item = HistoricalRecord.query\
        .options(joinedload(HistoricalRecord.donors).joinedload(DonorItem.donor))\
        .get_or_404(item_id)
    
    # Get configuration securely (no secrets exposed to template)
    config_data = {
        'PAYPAL_CLIENT_ID': current_app.config.get('PAYPAL_CLIENT_ID'),
        'EMAILJS_SERVICE_ID': current_app.config.get('EMAILJS_SERVICE_ID'),
        'EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL': current_app.config.get('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL'),
        'EMAILJS_API_ID': current_app.config.get('EMAILJS_API_ID'),
        'RECIPIENT_EMAILS': current_app.config.get('RECIPIENT_EMAILS')
    }
    
    logger.info(f"Displaying historical record {item_id}: {item.name}")
    
    return render_template(
        'Adopt_New_Yorks_Past/components/items/view_item.html',
        item=item,
        **config_data
    )

from flask import render_template, request
from flask_paginate import Pagination, get_page_parameter
from app.db.models import Bond

@main.route('/bonds', methods=['GET'])
@handle_errors
def get_bonds():
    """Display available bonds with optimized pagination"""
    # Validate pagination parameters
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = request.args.get('per_page', 9, type=int)
    
    pagination_params = validate_pagination_params(page, per_page, max_per_page=50)
    page = pagination_params['page']
    per_page = pagination_params['per_page']
    
    # Use SQLAlchemy pagination for better performance
    pagination = Bond.query\
        .filter_by(status='available')\
        .order_by(Bond.issue_date.desc(), Bond.bond_id)\
        .paginate(
            page=page,
            per_page=per_page,
            error_out=False,
            max_per_page=50
        )
    
    logger.info(f"Displaying bonds page {page}, {len(pagination.items)} bonds")
    
    return render_template(
        'Bonds/bonds_list.html',
        bonds=pagination.items,
        pagination=pagination
    )



@main.route('/bond/<bond_id>', methods=['GET'])
@handle_errors
def view_bond_details(bond_id):
    """View details of a specific bond with security validation"""
    # Sanitize bond_id input
    if not bond_id or not isinstance(bond_id, str) or len(bond_id.strip()) == 0:
        logger.warning(f"Invalid bond ID: {bond_id} from {request.remote_addr}")
        return render_template('Error_Pages/404_not_found.html'), 404
    
    bond_id = bond_id.strip()[:255]  # Limit length
    
    # Get bond
    bond = Bond.query.get_or_404(bond_id)
    
    # Get configuration securely
    config_data = {
        'PAYPAL_CLIENT_ID': current_app.config.get('PAYPAL_CLIENT_ID'),
        'EMAILJS_SERVICE_ID': current_app.config.get('EMAILJS_SERVICE_ID'),
        'EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL': current_app.config.get('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL'),
        'EMAILJS_API_ID': current_app.config.get('EMAILJS_API_ID'),
        'RECIPIENT_EMAILS': current_app.config.get('RECIPIENT_EMAILS')
    }
    
    logger.info(f"Displaying bond details for {bond_id}")
    
    return render_template(
        'Bonds/bond_details.html',
        bond=bond,
        **config_data
    )

@main.route('/events')
def events():
    # Render the events page template
    return render_template('Events/events.html')

@main.route('/contact')
def contact():
    """Render contact page with secure configuration"""
    config_data = {
        'EMAILJS_SERVICE_ID': current_app.config.get('EMAILJS_SERVICE_ID'),
        'EMAILJS_API_ID': current_app.config.get('EMAILJS_API_ID'),
        'RECIPIENT_EMAILS': current_app.config.get('RECIPIENT_EMAILS'),
        'EMAILJS_TEMPLATE_ID_FOR_CONTACT_FORM': current_app.config.get('EMAILJS_TEMPLATE_ID_FOR_CONTACT_FORM'),
    }
    
    return render_template('Contact/contact.html', **config_data)

@main.route('/koch-congressional-project')
def koch_congressional_project():
    # Render the Koch Congressional Project page template
    return render_template('Koch_Congressional_Project/koch_congressional_project.html')

@main.route('/contribute')
def contribute():
    # Render the contribute page template
    return render_template('Contribute/contribute.html')

@main.route('/central-park-book')
@handle_errors
def central_park_book():
    """Display Central Park Book page - finds the first available Central Park Book product"""
    try:
        # Find the Central Park Book regardless of quantity or availability status
        book = GeneralProduct.query.filter(
            GeneralProduct.name.icontains('Central Park')
        ).first()
        
        if not book:
            # If no Central Park Book found, look for any general product
            book = GeneralProduct.query.first()
            
        if not book:
            logger.warning("No general products found for Central Park Book page")
            # Create a basic error response instead of trying to render missing template
            return jsonify({'error': 'Central Park Book not found'}), 404
        
        # Configuration data for PayPal and EmailJS
        config_data = {
            'PAYPAL_CLIENT_ID': current_app.config.get('PAYPAL_CLIENT_ID'),
            'EMAILJS_SERVICE_ID': current_app.config.get('EMAILJS_SERVICE_ID'),
            'EMAILJS_API_ID': current_app.config.get('EMAILJS_API_ID'),
            'RECIPIENT_EMAILS': current_app.config.get('RECIPIENT_EMAILS'),
            'EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL': current_app.config.get('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL'),
        }
        
        return render_template(
            'Central_Park_Book/central_park_book.html',
            book=book,
            **config_data
        )
        
    except OperationalError as e:
        logger.error(f"Database error fetching Central Park Book: {str(e)}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching Central Park Book: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@main.route('/general-product/<product_id>')
@handle_errors
def general_product_details(product_id):
    """Display general product details page with PayPal integration"""
    if not validate_uuid(product_id):
        return render_template('Error_Pages/404.html'), 404
    
    # Get product with error handling
    try:
        book = GeneralProduct.query.get(product_id)
        if not book:
            logger.warning(f"General product not found: {product_id}")
            return render_template('Error_Pages/404.html'), 404
        
        # Configuration data for PayPal and EmailJS
        config_data = {
            'PAYPAL_CLIENT_ID': current_app.config.get('PAYPAL_CLIENT_ID'),
            'EMAILJS_SERVICE_ID': current_app.config.get('EMAILJS_SERVICE_ID'),
            'EMAILJS_API_ID': current_app.config.get('EMAILJS_API_ID'),
            'RECIPIENT_EMAILS': current_app.config.get('RECIPIENT_EMAILS'),
            'EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL': current_app.config.get('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL'),
        }
        
        return render_template(
            'Central_Park_Book/central_park_book.html',
            book=book,
            **config_data
        )
        
    except OperationalError as e:
        logger.error(f"Database error fetching general product {product_id}: {str(e)}")
        return render_template('Error_Pages/500.html'), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching general product {product_id}: {str(e)}")
        return render_template('Error_Pages/500.html'), 500

# Note: Error handlers are now centralized in app/__init__.py

from . import main
from flask import render_template, jsonify, request, current_app
import logging
from app.db.db import db
from app.db.models import HistoricalRecord, Donor, Transaction, DonorItem, Bond
import requests
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import text
from sqlalchemy.orm import joinedload  # Import joinedload for eager loading
from sqlalchemy.exc import OperationalError
import time
import os
from datetime import datetime

# Configurable parameter for pagination
PER_PAGE = 20

def get_paypal_access_token():
    """
    Retrieves an access token from PayPal using client credentials.
    This function fetches the PayPal access token required for making authorized API requests.
    It uses the client ID and secret key configured in the application's settings.
    Returns:
        str: The access token retrieved from PayPal.
    Raises:
        ValueError: If the PayPal API base URL is not set in the configuration.
        ValueError: If the request to retrieve the access token fails.
    Logs:
        Logs an error if the PayPal API base URL is not set.
        Logs an error if the request to retrieve the access token fails, including the status code and response text.
    """
    PAYPAL_CLIENT_ID = current_app.config.get('PAYPAL_CLIENT_ID')
    PAYPAL_CLIENT_SECRET_KEY = current_app.config.get('PAYPAL_CLIENT_SECRET_KEY')
    PAYPAL_API_BASE_URL = current_app.config.get('PAYPAL_API_BASE_URL')

    if not PAYPAL_API_BASE_URL:
        logging.error("PAYPAL_API_BASE_URL is not set in the configuration.")
        raise ValueError("PAYPAL_API_BASE_URL is not set!")
    
    auth_response = requests.post(
        f'{PAYPAL_API_BASE_URL}/v1/oauth2/token',
        headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
        data={'grant_type': 'client_credentials'},
        auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET_KEY)
    )
    
    if auth_response.status_code != 200:
        logging.error("Failed to retrieve PayPal access token. Status code: %s, Response: %s", auth_response.status_code, auth_response.text)
        raise ValueError("Failed to retrieve PayPal access token.")
    
    return auth_response.json().get('access_token')

@main.route('/create-order', methods=['POST'])
def create_order():
    access_token = get_paypal_access_token()
    PAYPAL_API_BASE_URL = current_app.config.get('PAYPAL_API_BASE_URL')

    if not PAYPAL_API_BASE_URL:
        logging.error("PAYPAL_API_BASE_URL is not set in the configuration.")
        return jsonify({'error': 'PAYPAL_API_BASE_URL is not set'}), 500

    # Obtener los detalles del artículo de la solicitud
    data = request.get_json()
    item_id = data.get('item_id')
    item_fee = data.get('fee')

    if not item_id or not item_fee:
        logging.error("Missing item ID or fee in the request payload. Data: %s", data)
        return jsonify({'error': 'Missing item ID or fee'}), 400

    # Crear la orden en PayPal
    order_response = requests.post(
        f'{PAYPAL_API_BASE_URL}/v2/checkout/orders',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        },
        json={
            'intent': 'CAPTURE',
            'purchase_units': [
                {
                    'reference_id': item_id,  
                    'amount': {
                        'currency_code': 'USD',
                        'value': item_fee
                    }
                }
            ]
        }
    )

    if order_response.status_code not in [200, 201]:
        logging.error("Failed to create PayPal order. Status code: %s, Response: %s", order_response.status_code, order_response.text)
        return jsonify({'error': 'Failed to create order with PayPal'}), order_response.status_code

    return jsonify(order_response.json())


@main.route('/capture-order/<order_id>', methods=['POST'])
def capture_order(order_id):
    try:
        with db.session.no_autoflush:
            # Check if this order has already been processed
            existing_transaction = Transaction.query.filter_by(
                paypal_transaction_id=order_id).first()
            if existing_transaction:
                return jsonify({'message': 'Order already processed'}), 200

            # Get data from request
            data = request.get_json()
            is_pickup = data.get('pickup', False)
            item_id = data.get('item_id')  # Extract item_id from request
            fee = data.get('fee')  # Extract fee from request
            
            access_token = get_paypal_access_token()
            PAYPAL_API_BASE_URL = current_app.config.get('PAYPAL_API_BASE_URL')
            if not PAYPAL_API_BASE_URL:
                logging.error("PAYPAL_API_BASE_URL not configured")
                return jsonify({'error': 'PayPal configuration missing'}), 500

            # Retrieve order details from PayPal
            order_details_response = requests.get(
                f'{PAYPAL_API_BASE_URL}/v2/checkout/orders/{order_id}',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                }
            )
            if order_details_response.status_code != 200:
                logging.error(f"Failed to get order details: {order_details_response.text}")
                return jsonify({'error': 'Failed to get order details'}), order_details_response.status_code

            order_details = order_details_response.json()
            capture_data = order_details if order_details.get('status') == 'COMPLETED' else None

            if not capture_data:
                # Rest of the existing capture code...
                pass

            # Extract phone number from PayPal response if available
            payer = capture_data.get('payer', {})
            phone = None
            
            # Try to get phone from PayPal's payer object
            if 'phone' in payer and 'phone_number' in payer['phone']:
                phone = payer['phone']['phone_number'].get('national_number')
            
            payer_email = payer.get('email_address')
            payer_name = f"{payer.get('name', {}).get('given_name', '')} {payer.get('name', {}).get('surname', '')}"

            # Extract shipping address from PayPal response
            purchase_units = capture_data.get('purchase_units', [])
            shipping = purchase_units[0].get('shipping', {}) if purchase_units else {}
            address = shipping.get('address', {})

            # Get or create donor using the payer's email
            donor = Donor.query.filter_by(donor_email=payer_email).first()
            if not donor:
                # New donor: Set shipping address and phone if available
                donor = Donor(
                    donor_name=payer_name,
                    donor_email=payer_email,
                    phone=phone,  # Now it's defined, either with a value or None
                    
                    # Set shipping address from PayPal data
                    shipping_street=address.get('address_line_1'),
                    shipping_apartment=address.get('address_line_2'),
                    shipping_city=address.get('admin_area_2'),
                    shipping_state=address.get('admin_area_1'),
                    shipping_zip_code=address.get('postal_code'),
                )
                db.session.add(donor)
            else:
                # For existing donors, update shipping address and phone if provided
                if address:
                    donor.shipping_street = address.get('address_line_1', donor.shipping_street)
                    donor.shipping_apartment = address.get('address_line_2', donor.shipping_apartment)
                    donor.shipping_city = address.get('admin_area_2', donor.shipping_city)
                    donor.shipping_state = address.get('admin_area_1', donor.shipping_state)
                    donor.shipping_zip_code = address.get('postal_code', donor.shipping_zip_code)
                
                # Update phone if provided
                if phone:
                    donor.phone = phone

            db.session.flush()

            try:
                with db.session.begin_nested():
                    transaction = Transaction(
                        paypal_transaction_id=order_id,
                        item_id=str(item_id),
                        donor_id=donor.donor_id,
                        fee=fee,
                        payment_status='COMPLETED',
                        payment_method='PayPal',
                        donor_email=payer_email,
                        pickup=is_pickup,  # Store pickup preference
                        timestamp=datetime.now()
                    )
                    db.session.add(transaction)
                    db.session.flush()

                    # Create a DonorItem record if the item is a historical record (UUID format)
                    if Transaction.is_uuid(item_id):
                        donor_item = DonorItem(
                            donor_id=donor.donor_id,
                            item_id=item_id,
                            fee=fee
                        )
                        db.session.add(donor_item)
                        db.session.flush()

                    # Update the item status depending on its type (HistoricalRecord or Bond)
                    if Transaction.is_uuid(item_id):
                        item = HistoricalRecord.query.get(item_id)
                        if item:
                            item.adopted = True
                    else:
                        item = Bond.query.get(item_id)
                        if item:
                            item.status = 'purchased'

                    if not item:
                        raise ValueError(f"Item {item_id} not found")

                db.session.commit()
                return jsonify({'message': 'Success'}), 200

            except Exception as db_error:
                db.session.rollback()
                logging.error(f"Database error: {str(db_error)}")
                return jsonify({'error': 'Database error'}), 500

    except Exception as e:
        logging.error(f"Capture error: {str(e)}")
        return jsonify({'error': 'Internal error'}), 500

@main.route('/')
def index():
    # Render the home page template
    return render_template('Index/index.html')

@main.route('/about')
def about():
    # Render the about page template
    return render_template('About/about.html')

@main.route('/adopt-new-yorks-past')
def new_yorks_past():
    try:
        page = request.args.get('page', type=int, default=1)
        per_page = 8

        # Query for non-adopted items only
        available_query = HistoricalRecord.query\
            .filter_by(adopted=False)\
            .options(joinedload(HistoricalRecord.donors).joinedload(DonorItem.donor))

        # Paginate available items
        pagination = available_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Separate query for adopted items
        adopted_items = HistoricalRecord.query\
            .filter_by(adopted=True)\
            .options(joinedload(HistoricalRecord.donors).joinedload(DonorItem.donor))\
            .all()

        return render_template(
            'Adopt_New_Yorks_Past/adopt_new_yorks_past.html',
            pagination=pagination,
            adopted_items=adopted_items
        )
        
    except Exception as e:
        logging.error(f"Unexpected error retrieving items: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500


@main.route('/adopt-new-yorks-past/item/<item_id>')
def new_yorks_past_view_item(item_id):
    PAYPAL_CLIENT_ID = current_app.config.get('PAYPAL_CLIENT_ID')
    EMAILJS_SERVICE_ID = current_app.config.get('EMAILJS_SERVICE_ID')
    EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL = current_app.config.get('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL')
    EMAILJS_API_ID = current_app.config.get('EMAILJS_API_ID')
    RECIPIENT_EMAILS = current_app.config.get('RECIPIENT_EMAILS')

    try:
        item = HistoricalRecord.query.get_or_404(item_id)
    except db.exc.OperationalError as e:
        logging.error("Database operational error while retrieving item with ID %s by user %s: %s", item_id, request.remote_addr, str(e))
        return jsonify({"error": "A database error occurred. Please try again later."}), 500
    except Exception as e:
        logging.error("Unexpected error retrieving item with ID %s by user %s: %s", item_id, request.remote_addr, str(e))
        return jsonify({"error": "An unexpected error occurred while trying to load the item. Please try refreshing the page or come back later."}), 500

    return render_template(
        'Adopt_New_Yorks_Past/components/items/view_item.html',
        item=item,
        EMAILJS_SERVICE_ID=EMAILJS_SERVICE_ID,
        EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL=EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL,
        EMAILJS_API_ID=EMAILJS_API_ID,
        PAYPAL_CLIENT_ID=PAYPAL_CLIENT_ID,
        RECIPIENT_EMAILS=RECIPIENT_EMAILS
    )

from flask import render_template, request
from flask_paginate import Pagination, get_page_parameter
from app.db.models import Bond

@main.route('/bonds', methods=['GET'])
def get_bonds():
    try:
        # Pagination setup
        page = request.args.get(get_page_parameter(), type=int, default=1)
        per_page = 9  # Number of items per page

        # Get total bonds count
        total_bonds = Bond.query.filter_by(status='available').count()

        # Calculate offset
        offset = (page - 1) * per_page

        # Get paginated results
        bonds = Bond.query.filter_by(status='available')\
            .order_by(Bond.bond_id)\
            .offset(offset)\
            .limit(per_page)\
            .all()

        # Create pagination object
        pagination = Pagination(
            page=page,
            per_page=per_page,
            total=total_bonds,
            css_framework='bootstrap5',
            record_name='bonds',
        )

        return render_template(
            'Bonds/bonds_list.html',
            bonds=bonds,
            pagination=pagination
        )

    except Exception as e:
        logging.error(f"Error fetching bonds: {str(e)}")
        return jsonify({'error': 'Unable to fetch bonds'}), 500



@main.route('/bond/<bond_id>', methods=['GET'])
def view_bond_details(bond_id):
    """
    View details of a specific bond, including PayPal integration and email notifications.
    """
    PAYPAL_CLIENT_ID = current_app.config.get('PAYPAL_CLIENT_ID')
    EMAILJS_SERVICE_ID = current_app.config.get('EMAILJS_SERVICE_ID')
    EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL = current_app.config.get('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL')
    EMAILJS_API_ID = current_app.config.get('EMAILJS_API_ID')
    RECIPIENT_EMAILS = current_app.config.get('RECIPIENT_EMAILS')

    try:
        bond = Bond.query.get_or_404(bond_id)
        return render_template(
            'Bonds/bond_details.html',
            bond=bond,
            PAYPAL_CLIENT_ID=PAYPAL_CLIENT_ID,
            EMAILJS_SERVICE_ID=EMAILJS_SERVICE_ID,
            EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL=EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL,
            EMAILJS_API_ID=EMAILJS_API_ID,
            RECIPIENT_EMAILS=RECIPIENT_EMAILS
        )
    except Exception as e:
        logging.error(f"Error fetching bond details: {str(e)}")
        return jsonify({'error': 'Unable to fetch bond details'}), 500

@main.route('/events')
def events():
    # Render the events page template
    return render_template('Events/events.html')

@main.route('/contact')
def contact():
    # Render the contact page template with the environment variables passed in
    return render_template(
        'Contact/contact.html',
        EMAILJS_SERVICE_ID=os.getenv('EMAILJS_SERVICE_ID'),
        EMAILJS_API_ID=os.getenv('EMAILJS_API_ID'),
        RECIPIENT_EMAILS=os.getenv('RECIPIENT_EMAILS'),
        EMAILJS_TEMPLATE_ID_FOR_CONTACT_FORM=os.getenv('EMAILJS_TEMPLATE_ID_FOR_CONTACT_FORM'),
    )

@main.route('/koch-congressional-project')
def koch_congressional_project():
    # Render the Koch Congressional Project page template
    return render_template('Koch_Congressional_Project/koch_congressional_project.html')

@main.route('/contribute')
def contribute():
    # Render the contribute page template
    return render_template('Contribute/contribute.html')

@main.app_errorhandler(404)
def http_error_handler(error):
    # Handle 404 errors by rendering the custom 404 error page
    return render_template("Error_Pages/404_not_found.html"), 404

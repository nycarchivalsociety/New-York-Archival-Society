from . import main
from flask import render_template, jsonify, request, current_app
import logging
from app.db.db import db
from app.db.models import Item, Donor, Transaction, DonorItem
from dotenv import load_dotenv, find_dotenv
import os
import requests
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import text
from sqlalchemy.orm import joinedload  # Import joinedload for eager loading
import re

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

    """
Creates a new PayPal order.
This route handles the creation of a new order using the PayPal API. It expects a JSON payload with the item ID and fee.
Returns:
    JSON response containing the order details if successful, or an error message if there was an issue.
Raises:
    400: If the request payload is missing the item ID or fee.
    500: If the PayPal API base URL is not set in the configuration.
    <status_code>: If the PayPal order creation fails, returns the status code from the PayPal API response.
Steps:
1. Retrieve the PayPal access token.
2. Get the PayPal API base URL from the application configuration.
3. Validate the presence of the item ID and fee in the request payload.
4. Make a POST request to the PayPal API to create the order.
5. Handle the response from the PayPal API and return the appropriate JSON response.
"""

    access_token = get_paypal_access_token()
    PAYPAL_API_BASE_URL = current_app.config.get('PAYPAL_API_BASE_URL')

    if not PAYPAL_API_BASE_URL:
        logging.error("PAYPAL_API_BASE_URL is not set in the configuration.")
        return jsonify({'error': 'PAYPAL_API_BASE_URL is not set'}), 500
    
    # Get the item details from the request payload
    data = request.get_json()
    item_id = data.get('item_id')
    item_fee = data.get('fee')

    if not item_id or not item_fee:
        logging.error("Missing item ID or fee in the request payload. Data: %s", data)
        return jsonify({'error': 'Missing item ID or fee'}), 400

    order_response = requests.post(
        f'{PAYPAL_API_BASE_URL}/v2/checkout/orders',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}'
        },
        json={
            'intent': 'CAPTURE',
            'purchase_units': [{'reference_id': item_id, 'amount': {'currency_code': 'USD', 'value': item_fee}}]
        }
    )

    if order_response.status_code not in [200, 201]:
        logging.error("Failed to create PayPal order. Status code: %s, Response: %s", order_response.status_code, order_response.text)
        return jsonify({'error': 'Failed to create order with PayPal'}), order_response.status_code

    return jsonify(order_response.json())

@main.route('/capture-order/<order_id>', methods=['POST'])
def capture_order(order_id):
    try:
        access_token = get_paypal_access_token()
        PAYPAL_API_BASE_URL = current_app.config.get('PAYPAL_API_BASE_URL')

        if not PAYPAL_API_BASE_URL:
            logging.error("PAYPAL_API_BASE_URL is not set in the configuration.")
            return jsonify({'error': 'PAYPAL_API_BASE_URL is not set'}), 500
        
        capture_response = requests.post(
            f'{PAYPAL_API_BASE_URL}/v2/checkout/orders/{order_id}/capture',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
        )
        capture_data = capture_response.json()

        # Handle already captured orders by getting the order details
        if capture_response.status_code == 422 and capture_data.get('name') == 'UNPROCESSABLE_ENTITY' and any(detail.get('issue') == 'ORDER_ALREADY_CAPTURED' for detail in capture_data.get('details', [])):
            logging.warning("Order already captured. Order ID: %s", order_id)
            # Fetch the existing order details to proceed with database updates
            order_details_response = requests.get(
                f'{PAYPAL_API_BASE_URL}/v2/checkout/orders/{order_id}',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                }
            )
            if order_details_response.status_code != 200:
                logging.error("Failed to retrieve PayPal order details for already captured order. Status code: %s, Response: %s", order_details_response.status_code, order_details_response.text)
                return jsonify({'error': 'Failed to retrieve order details for already captured order.'}), order_details_response.status_code
            capture_data = order_details_response.json()
        elif capture_response.status_code != 201:
            # If capture was not successful, and it is not an already captured order
            logging.error("Failed to capture PayPal order. Status code: %s, Response: %s", capture_response.status_code, capture_response.text)
            return jsonify({'error': 'Failed to capture order. Please check the order ID or contact support.'}), capture_response.status_code

        # Extract payer information from capture response
        payer = capture_data.get('payer', {})
        payment_source = capture_data.get('payment_source', {})
        payment_status = capture_data.get('status', 'Unknown')

        payment_method = "Unknown"
        if 'paypal' in payment_source:
            payment_method = 'PayPal Account'
        elif 'card' in payment_source:
            payment_method = 'Credit/Debit Card'

        # Prepare transaction data
        item_id = capture_data.get('purchase_units', [{}])[0].get('reference_id', None)
        fee = capture_data.get('purchase_units', [{}])[0].get('payments', {}).get('captures', [{}])[0].get('amount', {}).get('value', None)
        payer_email = payer.get('email_address', None)
        payer_name = f"{payer.get('name', {}).get('given_name', '')} {payer.get('name', {}).get('surname', '')}"
        paypal_transaction_id = capture_data.get('purchase_units', [{}])[0].get('payments', {}).get('captures', [{}])[0].get('id', None)

        if not item_id or not fee or not paypal_transaction_id:
            logging.error("Invalid capture response, missing critical information. Item ID: %s, Fee: %s, Transaction ID: %s", item_id, fee, paypal_transaction_id)
            return jsonify({'error': 'Invalid capture response, missing critical information.'}), 400

        # Normalize email to prevent duplicate entries due to casing/whitespace differences
        normalized_email = payer_email.strip().lower() if payer_email else None

        # Fetch the item from the database using the item ID
        item = Item.query.filter_by(id=item_id).one_or_none()  # Find the item by ID, return None if not found
        if not item:
            logging.error("Item not found in the database. Item ID: %s", item_id)
            return jsonify({'error': 'Item not found'}), 404

        # Check if the donor already exists by searching with the normalized email
        donor = Donor.query.filter_by(donor_email=normalized_email).first() if normalized_email else None
        if not donor:
            # Create a new donor if none exists with the given email
            donor = Donor(
                donor_name=payer_name,
                donor_email=normalized_email
            )
            db.session.add(donor)
            try:
                db.session.flush()  # Ensure the donor_id is generated before proceeding
                logging.info("Donor created successfully. Donor ID: %s", donor.donor_id)
            except Exception as e:
                # Rollback if an error occurs during flush
                db.session.rollback()
                logging.error("Error flushing donor: %s. Data: donor_name=%s, donor_email=%s", str(e), payer_name, normalized_email)
                return jsonify({'error': 'An error occurred while creating the donor: {}'.format(str(e))}), 500

        # Link donor with the item by creating a DonorItem instance
        new_donor_item = DonorItem(
            donor_id=donor.donor_id,  # Link to the donor
            item_id=item_id,  # Link to the item
            fee=fee  # Store the fee provided by the donor
        )
        db.session.add(new_donor_item)
        logging.info("DonorItem created successfully. Donor ID: %s, Item ID: %s", donor.donor_id, item_id)

        # Mark the item as adopted since a donor has now been linked to it
        item.adopted = True
        logging.info("Item marked as adopted. Item ID: %s", item_id)

        # Create a new transaction linked to the existing or new donor
        transaction = Transaction(
            paypal_transaction_id=paypal_transaction_id,  # Store PayPal transaction ID
            item_id=item_id,  # Link to the item
            donor_id=donor.donor_id,  # Link to the donor
            fee=fee,  # Store the fee for the transaction
            payment_status=payment_status,  # Store the status of the payment
            payment_method=payment_method,  # Correctly store the payment method used
            donor_email=normalized_email  # Store the donor's email
        )
        db.session.add(transaction)

        # Commit all changes to the database at once to optimize performance
        db.session.commit()

        # Return a success response
        return jsonify({'message': 'Order captured and transaction processed successfully'}), 200

    except Exception as e:
        # Rollback the main transaction in case of error
        db.session.rollback()
        logging.error("Error capturing order: %s. Data: order_id=%s. Rolling back changes.", str(e), order_id)
        # Return an error response
        return jsonify({'error': 'An error occurred while capturing the order: {}'.format(str(e))}), 500

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
    """
    Render the Adopt New York's Past page with paginated items.
    Each item displays its adoption status and donors.
    """
    # Get the current page number from the request, default to 1
    page = request.args.get(get_page_parameter(), type=int, default=1)
    
    try:
        # Query the total number of items to correctly set pagination
        total_items = Item.query.count()

        # Calculate offset based on the current page
        offset = (page - 1) * PER_PAGE

        # Fetch items for the current page with eager loading of donors
        items_query = Item.query.options(
            joinedload(Item.donors).joinedload(DonorItem.donor)
        ).limit(PER_PAGE).offset(offset).all()

        # If no items are found on a non-first page, return a 404 error
        if not items_query and page != 1:
            return jsonify({"error": "The requested page is out of range. Please try a valid page number."}), 404

        # Initialize the Pagination object with the correct total
        pagination = Pagination(
            page=page,
            total=total_items,
            record_name='items',
            per_page=PER_PAGE,
            css_framework='bootstrap4'  # Adjust based on your frontend framework
        )

        # Render the template with the fetched items and pagination
        return render_template(
            'Adopt_New_Yorks_Past/adopt_new_yorks_past.html',
            items=items_query,
            pagination=pagination
        )
    
    except db.exc.OperationalError as e:
        logging.error(
            "Database operational error while retrieving items for page %s by user %s: %s",
            page, request.remote_addr, str(e)
        )
        return jsonify({"error": "A database error occurred. Please try again later."}), 500
    
    except Exception as e:
        logging.error(
            "Unexpected error retrieving items for page %s by user %s: %s",
            page, request.remote_addr, str(e)
        )
        return jsonify({"error": "An unexpected error occurred while trying to load items. Please try refreshing the page or come back later."}), 500

@main.route('/adopt-new-yorks-past/item/<item_id>')
def new_yorks_past_view_item(item_id):
    """Render the item view page for adopting New York's past."""
    # Retrieve PayPal and EmailJS credentials from app config
    PAYPAL_CLIENT_ID = current_app.config.get('PAYPAL_CLIENT_ID')
    EMAILJS_SERVICE_ID = current_app.config.get('EMAILJS_SERVICE_ID')
    EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL = current_app.config.get('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL')
    EMAILJS_API_ID = current_app.config.get('EMAILJS_API_ID')
    RECIPIENT_EMAILS = current_app.config.get('RECIPIENT_EMAILS')

    # Query the database for the specified item by ID
    try:
        item = Item.query.get_or_404(item_id)  # Get item by ID or return a 404 error if not found
    except db.exc.OperationalError as e:
        logging.error("Database operational error while retrieving item with ID %s by user %s: %s", item_id, request.remote_addr, str(e))  # Log the error with more context
        return jsonify({"error": "A database error occurred. Please try again later."}), 500  # Specific database error message
    except Exception as e:
        logging.error("Unexpected error retrieving item with ID %s by user %s: %s", item_id, request.remote_addr, str(e))  # Log the error with more context
        return jsonify({"error": "An unexpected error occurred while trying to load the item. Please try refreshing the page or come back later."}), 500  # Return a 500 response with user-friendly message

    # Render the view item template with the found item and EmailJS variables
    return render_template(
        'Adopt_New_Yorks_Past/components/items/view_item.html',
        item=item,
        EMAILJS_SERVICE_ID=EMAILJS_SERVICE_ID,
        EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL=EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL,
        EMAILJS_API_ID=EMAILJS_API_ID,
        PAYPAL_CLIENT_ID=PAYPAL_CLIENT_ID,
        RECIPIENT_EMAILS=RECIPIENT_EMAILS
    )

@main.route('/events')
def events():
    # Render the events page template
    return render_template('Events/events.html')

@main.route('/contact')
def contact():
    # Render the contact page template with the environment variables passed in
    return render_template(
        'Contact/contact.html',
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
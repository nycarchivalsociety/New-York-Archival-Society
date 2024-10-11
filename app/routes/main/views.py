# main_routes.py
from . import main
from flask import render_template, jsonify, request, current_app
import logging
from app.db.models import Items, Donors, Transactions
from app.db.db import db
from dotenv import load_dotenv
import os  
from flask_paginate import Pagination, get_page_parameter  # Import for pagination

# Load environment variables
if os.path.exists('.env.development'):
    load_dotenv('.env.development')
else:
    load_dotenv('.env')

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
    # Query all items from the database, including their donors, with pagination
    page = request.args.get(get_page_parameter(), type=int, default=1)  # Get the current page number from the request
    items = Items.query.paginate(page=page, per_page=20)  # Paginate the items, 20 items per page
    pagination = Pagination(page=page, total=items.total, record_name='items', per_page=20)  # Create pagination object
    return render_template('Adopt_New_Yorks_Past/adopt_new_yorks_past.html', items=items.items, pagination=pagination)

@main.route('/adopt-new-yorks-past/item/<item_id>')
def new_yorks_past_view_item(item_id):
    """Render the item view page for adopting New York's past."""
    # Retrieve PayPal and EmailJS credentials from app config
    PAYPAL_CLIENT_ID = current_app.config.get('PAYPAL_CLIENT_ID')
    EMAILJS_SERVICE_ID = current_app.config.get('EMAILJS_SERVICE_ID')
    EMAILJS_TEMPLATE_ID = current_app.config.get('EMAILJS_TEMPLATE_ID')
    EMAILJS_API_ID = current_app.config.get('EMAILJS_API_ID')
    RECIPIENT_EMAILS = current_app.config.get('RECIPIENT_EMAILS')

    # Query the database for the specified item by ID
    try:
        item = Items.query.get_or_404(item_id)  # Get item by ID or return a 404 error if not found
    except Exception as e:
        logging.error("Error retrieving item: %s", str(e))  # Log the error
        return jsonify({"error": "Database error"}), 500  # Return a 500 response if there's a database error

    # Render the view item template with the found item and EmailJS variables
    return render_template(
        'adopt_new_yorks_past/components/items/view_item.html',
        item=item,
        EMAILJS_SERVICE_ID=EMAILJS_SERVICE_ID,
        EMAILJS_TEMPLATE_ID=EMAILJS_TEMPLATE_ID,
        EMAILJS_API_ID=EMAILJS_API_ID,
        PAYPAL_CLIENT_ID=PAYPAL_CLIENT_ID,
        RECIPIENT_EMAILS=RECIPIENT_EMAILS
    )

@main.route('/process-transaction', methods=['POST'])
def process_transaction():
    try:
        data = request.get_json()  # Get JSON data from the request

        # Extract transaction details
        item_id = data.get('item_id')
        fee = data.get('fee')
        payer_email = data.get('payer_email')
        payer_name = data.get('payer_name')
        payment_status = data.get('payment_status')
        payment_method = data.get('payment_method')
        paypal_transaction_id = data.get('transaction_id')  # Use PayPal's transaction ID

        # Fetch the item from the database
        item = Items.query.filter_by(id=item_id).first()  # Find the item by ID
        if not item:
            return jsonify({'error': 'Item not found'}), 404  # Return a 404 response if item is not found

        # Check if the donor already exists
        donor = Donors.query.filter_by(donor_email=payer_email).first()  # Check if a donor with the given email already exists
        if not donor:
            # Create a new donor if none exists
            donor = Donors(
                donor_name=payer_name,
                donor_email=payer_email,
                item_id=item_id,
                fee=fee
            )
            db.session.add(donor)
            db.session.commit()  # Commit donor separately to ensure donor_id is available
        else:
            # Update donor's item_id and fee (if necessary)
            donor.item_id = item_id
            donor.fee = fee

        # Mark the item as adopted
        item.adopted = True

        # Create a new transaction
        transaction = Transactions(
            paypal_transaction_id=paypal_transaction_id,
            item_id=item_id,
            donor_id=donor.donor_id,
            fee=fee,
            payment_status=payment_status,
            payment_method=payment_method,
            donor_email=payer_email
        )
        db.session.add(transaction)

        # Commit all changes
        db.session.commit()

        return jsonify({'message': 'Transaction processed successfully'}), 200  # Return success response

    except Exception as e:
        db.session.rollback()  # Roll back the transaction in case of error
        logging.error("Error processing transaction: %s. Rolling back changes.", str(e))  # Log the error
        return jsonify({'error': 'An error occurred while processing the transaction: {}'.format(str(e))}), 500  # Return error response
    
@main.route('/events')
def events():
    # Render the events page template
    return render_template('Events/events.html')

@main.route('/contact')
def contact():
    # Render the contact page template
    return render_template('Contact/contact.html')

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

# Add index to optimize query performance on donor_email
db.Index('idx_donor_email', Donors.donor_email)
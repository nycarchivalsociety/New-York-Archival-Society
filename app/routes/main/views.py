from . import main
from flask import render_template, jsonify, request, current_app
import logging
from app.db.db import db
from app.db.models import Item, Donor, Transaction, DonorItem
from dotenv import load_dotenv, find_dotenv
import os
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import text
from sqlalchemy.orm import joinedload  # Import joinedload for eager loading
import re

# Load environment variables
load_dotenv(find_dotenv())

# Configurable parameter for pagination
PER_PAGE = 20

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

@main.route('/process-transaction', methods=['POST'])
def process_transaction():
    try:
        data = request.get_json()  # Get JSON data from the request

        # Validate required fields
        required_fields = ['item_id', 'fee', 'payer_email', 'payer_name', 'payment_status', 'payment_method', 'transaction_id']
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            # Return an error if any required fields are missing
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Extract transaction details from the request data
        item_id = data.get('item_id')
        fee = data.get('fee')
        payer_email = data.get('payer_email')
        payer_name = data.get('payer_name')
        payment_status = data.get('payment_status')
        payment_method = data.get('payment_method')  # Correctly fetch payment method from request
        paypal_transaction_id = data.get('transaction_id')  # Use PayPal's transaction ID

        # Normalize email to prevent duplicate entries due to casing/whitespace differences
        normalized_email = payer_email.strip().lower()

        # Fetch the item from the database using the item ID
        item = Item.query.filter_by(id=item_id).one_or_none()  # Find the item by ID, return None if not found
        if not item:
            # Return an error if the item is not found
            return jsonify({'error': 'Item not found'}), 404

        # Check if the donor already exists by searching with the normalized email
        donor = Donor.query.filter_by(donor_email=normalized_email).first()
        if not donor:
            # Create a new donor if none exists with the given email
            donor = Donor(
                donor_name=payer_name,
                donor_email=normalized_email
            )
            db.session.add(donor)
            try:
                db.session.flush()  # Ensure the donor_id is generated before proceeding
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

        # Mark the item as adopted since a donor has now been linked to it
        item.adopted = True

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
        return jsonify({'message': 'Transaction processed successfully'}), 200

    except Exception as e:
        # Save failed transaction in case of error
        try:
            failed_transaction = Transaction(
                paypal_transaction_id=paypal_transaction_id,  # Store PayPal transaction ID even if failed
                item_id=item_id,  # Link to the item
                donor_id=donor.donor_id if 'donor' in locals() else None,  # Link to donor if available
                fee=fee,  # Store the fee even if the transaction failed
                payment_status='Failed',  # Mark the payment status as failed
                payment_method=payment_method,  # Store the payment method used
                donor_email=normalized_email  # Store the donor's email
            )
            db.session.add(failed_transaction)
            db.session.commit()  # Commit the failed transaction to the database
        except Exception as commit_error:
            # Log an error if saving the failed transaction also fails
            logging.error("Error saving failed transaction: %s. Data: paypal_transaction_id=%s, item_id=%s, fee=%s, payment_method=%s, donor_email=%s", str(commit_error), paypal_transaction_id, item_id, fee, payment_method, normalized_email)
            db.session.rollback()

        # Rollback the main transaction in case of error
        db.session.rollback()
        logging.error("Error processing transaction: %s. Data: item_id=%s, fee=%s, payer_email=%s, payer_name=%s, payment_status=%s, payment_method=%s, transaction_id=%s. Rolling back changes.", str(e), item_id, fee, payer_email, payer_name, payment_status, payment_method, paypal_transaction_id)
        # Return an error response
        return jsonify({'error': 'An error occurred while processing the transaction: {}'.format(str(e))}), 500

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

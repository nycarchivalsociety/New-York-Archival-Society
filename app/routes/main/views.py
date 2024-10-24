# main_routes.py
from . import main
from flask import render_template, jsonify, request, current_app
import logging
from app.db.db import db
from app.db.models import Items, Donors, Transactions
from dotenv import load_dotenv, find_dotenv
import os
from flask_paginate import Pagination, get_page_parameter
from sqlalchemy import text

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
    # Query all items from the database, including their donors, with pagination
    page = request.args.get(get_page_parameter(), type=int, default=1)  # Get the current page number from the request
    try:
        items = Items.query.paginate(page=page, per_page=PER_PAGE, error_out=False)  # Paginate the items with error_out disabled to avoid exceptions
        if not items.items and page != 1:
            return jsonify({"error": "The requested page is out of range. Please try a valid page number."}), 404
        pagination = Pagination(page=page, total=items.total, record_name='items', per_page=PER_PAGE)  # Create pagination object
        return render_template('Adopt_New_Yorks_Past/adopt_new_yorks_past.html', items=items.items, pagination=pagination)
    except db.exc.OperationalError as e:
        logging.error("Database operational error while retrieving items for page %s by user %s: %s", page, request.remote_addr, str(e))  # Log the error with more context
        return jsonify({"error": "A database error occurred. Please try again later."}), 500  # Specific database error message
    except Exception as e:
        logging.error("Unexpected error retrieving items for page %s by user %s: %s", page, request.remote_addr, str(e))  # Log the error with more context
        return jsonify({"error": "An unexpected error occurred while trying to load items. Please try refreshing the page or come back later."}), 500  # Return a 500 response with user-friendly message

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
        item = Items.query.get_or_404(item_id)  # Get item by ID or return a 404 error if not found
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

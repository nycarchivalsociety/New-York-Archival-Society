# app/routes/main/routes.py

from . import main
from flask import render_template, request, jsonify
from app.db.models import Items, Donors
from app.db.connection import db
import uuid
import os
import requests
from requests.auth import HTTPBasicAuth
from sqlalchemy.exc import SQLAlchemyError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


# Image URLs (consider moving this to a separate config or data file if it's large)
image_urls = [
    "https://images.squarespace-cdn.com/content/v1/57ade572bebafb370ceb883f/1499865908939-KIXLCIC5P6MX75NTD1DY/image-asset.jpeg?format=750w",
    "https://images.squarespace-cdn.com/content/v1/57ade572bebafb370ceb883f/1500315427919-FSR0F60L6LO2VY0DA9LQ/image-asset.jpeg?format=750w",
    "https://images.squarespace-cdn.com/content/v1/57ade572bebafb370ceb883f/1499869039027-OG3Y2ZDDQ8JXSMC34ZSR/image-asset.jpeg?format=750w",
    "https://images.squarespace-cdn.com/content/v1/57ade572bebafb370ceb883f/1499952153133-5I3ZF5R57EOHLMXS123B/image-asset.jpeg?format=750w",
    "https://images.squarespace-cdn.com/content/v1/57ade572bebafb370ceb883f/1499866535035-PPKLZQFWY105YHIOK812/bpb_02227.jpg?format=750w",
    "https://images.squarespace-cdn.com/content/v1/57ade572bebafb370ceb883f/1499952663011-FPYTNCK8WUA0QZ1T0V4S/image-asset.jpeg?format=750w",
    "https://images.squarespace-cdn.com/content/v1/57ade572bebafb370ceb883f/1500387041163-T3LVK0OLTOL208Y5XD5C/image-asset.jpeg?format=750w",
    "https://images.squarespace-cdn.com/content/v1/57ade572bebafb370ceb883f/1500394141473-IGOMN7FHRIZYKA0WNF5V/animalsnip3.JPG?format=750w",
]

@main.route('/capture-order', methods=['POST'])
def capture_order():
    try:
        data = request.get_json()
        if not data:
            logging.error("No JSON payload received")
            return jsonify({"error": "No JSON payload received"}), 400

        order_id = data.get('orderID')
        item_id = data.get('item_id')

        # Validate input data
        if not order_id or not item_id:
            logging.error("Invalid input data: orderID or item_id missing")
            return jsonify({"error": "Invalid input data"}), 400

        # Get PayPal access token
        access_token = get_paypal_access_token()
        if not access_token:
            logging.error("Unable to obtain PayPal access token")
            return jsonify({"error": "Unable to obtain PayPal access token"}), 500

        # Capture the order
        capture_response = capture_paypal_order(order_id, access_token)
        if 'error' in capture_response:
            logging.error("Failed to capture PayPal order: %s", capture_response['error'])
            return jsonify({"error": "Failed to capture order"}), 400

        # Extract payer information
        payer_info = capture_response.get('payer', {})
        donor_name = f"{payer_info.get('name', {}).get('given_name', '')} {payer_info.get('name', {}).get('surname', '')}".strip()
        donor_name = donor_name or "Anonymous"

        # Update item status and create donor record
        item = Items.query.filter_by(id=item_id).first()
        if item:
            item.adopted = True

            new_donor = Donors(
                donor_id=str(uuid.uuid4()),
                donor_name=donor_name,
                item_id=item.id
            )
            db.session.add(new_donor)
            db.session.commit()

            return jsonify({"success": True}), 200
        else:
            logging.error("Item not found with ID: %s", item_id)
            return jsonify({"error": "Item not found"}), 404
    except SQLAlchemyError as e:
        logging.error("Database error: %s", str(e))
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        logging.error("Error in capture_order: %s", str(e))
        return jsonify({"error": "Internal server error"}), 500
    
def get_paypal_access_token():
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
    PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET')
    PAYPAL_OAUTH_API = 'https://api-m.sandbox.paypal.com/v1/oauth2/token'  # Use sandbox URL for testing

    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        logging.error("PayPal Client ID or Secret is missing.")
        return None

    auth = HTTPBasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en_US",
    }
    data = {
        "grant_type": "client_credentials"
    }
    try:
        response = requests.post(PAYPAL_OAUTH_API, headers=headers, data=data, auth=auth)
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            logging.error("Failed to obtain PayPal access token: %s", response.text)
            return None
    except Exception as e:
        logging.error("Exception during PayPal access token retrieval: %s", str(e))
        return None

def capture_paypal_order(order_id, access_token):
    PAYPAL_ORDER_API = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture'  # Use sandbox URL for testing
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    try:
        response = requests.post(PAYPAL_ORDER_API, headers=headers)
        if response.status_code in [200, 201]:
            return response.json()
        else:
            logging.error("Failed to capture PayPal order: %s", response.text)
            return {"error": response.text}
    except Exception as e:
        logging.error("Exception during PayPal order capture: %s", str(e))
        return {"error": str(e)}

@main.route('/adopt-new-yorks-past/item/<item_id>')
def new_yorks_past_view_item(item_id):

    EMAILJS_SERVICE_ID = os.getenv('EMAILJS_SERVICE_ID')
    EMAILJS_TEMPLATE_ID = os.getenv('EMAILJS_TEMPLATE_ID')
    EMAILJS_API_ID = os.getenv('EMAILJS_API_ID')

    # Query the database for an item by its UUID
    item = Items.query.filter_by(id=item_id).first()
    
    # If no item is found, return a 404 error
    if item is None:
        return "Item not found", 404


    print(os.getenv('EMAILJS_SERVICE_ID'))
    print(os.getenv('EMAILJS_TEMPLATE_ID'))
    print(os.getenv('EMAILJS_API_ID'))

    # Render the template with the found item and EmailJS variables
    return render_template(
        'adopt_new_yorks_past/components/items/view_item.html',
        item=item,
        EMAILJS_SERVICE_ID=EMAILJS_SERVICE_ID,
        EMAILJS_TEMPLATE_ID=EMAILJS_TEMPLATE_ID,
        EMAILJS_API_ID=EMAILJS_API_ID
    )


@main.route('/')
def index():
    return render_template('main/index.html')

@main.route('/update_adoption_status', methods=['POST'])
def update_adoption_status():
    data = request.json
    item_id = data.get('item_id')
    adopted_status = data.get('adopted')  # Expecting a boolean value
    donor_name = data.get('donor_name')  # Optional if adopted is False

    # Validate input data
    if adopted_status is None:
        return jsonify({"error": "Adopted status is required"}), 400

    # Find the item by ID
    item = Items.query.filter_by(id=item_id).first()
    if not item:
        return jsonify({"error": "Item not found"}), 404

    if adopted_status:
        # If adopted is True, create a new donor record
        if not donor_name:
            return jsonify({"error": "Donor name is required when adopting an item"}), 400

        item.adopted = True
        db.session.commit()

        new_donor = Donors(
            donor_id=str(uuid.uuid4()),
            donor_name=donor_name,
            item_id=item.id
        )
        db.session.add(new_donor)
        db.session.commit()
    else:
        # If adopted is False, delete donor records related to the item
        Donors.query.filter_by(item_id=item.id).delete()
        db.session.commit()
        
        # Update the item status to not adopted
        item.adopted = False
        db.session.commit()

    return jsonify({"success": True})


@main.route('/projects')
def projects():
    return render_template('main/projects.html')

@main.route('/adopt-new-yorks-past')
def new_yorks_past():
    # Query all items from the database, including their donors
    items = Items.query.all()
    return render_template('adopt_new_yorks_past/adopt_new_yorks_past.html', image_urls=image_urls, items=items)

@main.route('/events')
def events():
    return render_template('events/events.html', image_urls=image_urls)

@main.route('/contact')
def contact():
    return render_template('contact/contact.html')

@main.route('/koch-congressional-project')
def koch_congressional_project():
    return render_template('koch_congressional_project/koch_congressional_project.html')

@main.route('/about')
def about():
    return render_template('about/about.html')

@main.route('/contribute')
def contribute():
    return render_template('contribute/contribute.html')

@main.app_errorhandler(404)
def http_error_handler(error):
    return render_template("error/404NotFound.html"), 404

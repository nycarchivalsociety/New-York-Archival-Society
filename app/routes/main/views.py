# main_routes.py
# now you can import the products module
from app.data.items import items
from . import main
from flask import render_template
from dotenv import load_dotenv
import os


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



# Load environment variables
load_dotenv()

# Database connection parameters
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')


@main.route('/')
def index():
    return render_template('main/index.html')


@main.route('/board-of-directors')
def boardofdirectors():
    return render_template('main/board-of-directors.html')


@main.route('/projects')
def projects():
    return render_template('projects.html')



@main.route('/adopt-new-yorks-past')
def new_yorks_past():
    return render_template('main/adopt_new_yorks_past.html', image_urls=image_urls, items=items)

@main.route('/adopt-new-yorks-past/item/<item_id>')
def new_yorks_past_view_item(item_id):
    item = next((item for item in items if str(item['id']) == item_id), None)  # Assuming each item has an 'id' key
    if item is None:
        return "Item not found", 404
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')  # Assuming you have the PayPal client ID in an environment variable
    return render_template('items/view_item.html', item=item, PAYPAL_CLIENT_ID=PAYPAL_CLIENT_ID)


@main.route('/events')
def events():
    return render_template('main/events.html', image_urls=image_urls)


@main.route('/contact')
def contact():
    return render_template('main/contact.html')


@main.route('/koch-congressional-project')
def koch_congressional_project():
    return render_template('main/koch_congressional_project.html')


@main.route('/about')
def about():
    return render_template('main/about.html')


@main.route('/contribute')
def contribute():
    return render_template('main/contribute.html')


@main.app_errorhandler(404)
def http_error_handler(error):
    return render_template("error/404NotFound.html"), 404

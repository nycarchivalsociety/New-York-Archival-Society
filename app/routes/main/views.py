# main_routes.py
from . import main
from flask import render_template
from dotenv import load_dotenv
import os
from app.data.items import items


# Load environment variables
load_dotenv()


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
  
    return render_template('Adopt_New_Yorks_Past/adopt_new_yorks_past.html',  items=items)

@main.route('/adopt-new-yorks-past/item/<item_id>')
def new_yorks_past_view_item(item_id):
   # PayPal client ID
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID')
    item = next((item for item in items if item['id'] == item_id), None)
    if item is None:
        return "Item not found", 404
    return render_template(
        'Adopt_New_Yorks_Past/components/items/view_item.html',
        item=item,
        PAYPAL_CLIENT_ID=PAYPAL_CLIENT_ID,
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


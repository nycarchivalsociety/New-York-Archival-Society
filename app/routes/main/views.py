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
   
    return render_template('adopt_new_yorks_past/adopt_new_yorks_past.html')


    
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
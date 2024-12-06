from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv, find_dotenv
import os
import logging
from app.db.db import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    # Load environment variables from .env.development if it exists, else from .env
    env_file = find_dotenv('.env.development') or find_dotenv('.env')
    if env_file:
        logger.info(f"Loading environment from: {env_file}")
        load_dotenv(env_file, override=True)
    else:
        logger.info("No .env file found, using system environment variables")

    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Configuration settings with enhanced error handling
    database_uri = os.environ.get('DATABASE_URI')

    if not database_uri:
        logger.error("DATABASE_URI environment variable is not set!")
        logger.debug("Available environment variables: " + ", ".join([k for k in os.environ.keys()]))
        raise ValueError("Database URI is not configured. Please set DATABASE_URI in your environment variables.")

    # Update the app configuration before initializing the database
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            'pool_size': 5,
            'max_overflow': 0,
            'pool_timeout': 30,
            'pool_recycle': 1800,
            'pool_pre_ping': True,
        },
        SECRET_KEY=os.getenv('SECRET_KEY', 'default-dev-key'),
        PAYPAL_CLIENT_ID=os.getenv('PAYPAL_CLIENT_ID'),
        EMAILJS_SERVICE_ID=os.getenv('EMAILJS_SERVICE_ID'),
        EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL=os.getenv('EMAILJS_TEMPLATE_ID_FOR_PAYPAL_CONFIRMATION_EMAIL'),
        EMAILJS_TEMPLATE_ID_FOR_CONTACT_FORM=os.getenv('EMAILJS_TEMPLATE_ID_FOR_CONTACT'),
        EMAILJS_API_ID=os.getenv('EMAILJS_API_ID'),
        RECIPIENT_EMAILS=os.getenv('RECIPIENT_EMAILS'),
        PAYPAL_CLIENT_SECRET_KEY=os.getenv('PAYPAL_CLIENT_SECRET_KEY'),
        PAYPAL_API_BASE_URL=os.getenv('PAYPAL_API_BASE_URL')
    )

    # Initialize the database after configuration is set
    db.init_app(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Import models within app context
    with app.app_context():
        from app.db import models

    # Register blueprints
    from .routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    logger.info("Application created successfully")
    return app
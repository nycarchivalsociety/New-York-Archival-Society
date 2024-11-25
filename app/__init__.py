from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from app.db.db import db

def create_app():
    # Check for .env.development first, then fall back to .env
    base_path = os.path.dirname(os.path.dirname(__file__))
    dev_env_path = os.path.join(base_path, '.env.development')
    prod_env_path = os.path.join(base_path, '.env')
    
    if os.path.exists(dev_env_path):
        env_path = dev_env_path
        print("Using development environment variables")
    elif os.path.exists(prod_env_path):
        env_path = prod_env_path
        print("Using production environment variables")
    else:
        raise RuntimeError("No .env or .env.development file found!")
    
    load_dotenv(env_path, override=True)

    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Load configuration settings
    app.config.from_object('app.config.Config')

    # Initialize the database
    db.init_app(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Import models to register them with the app
    with app.app_context():
        from app.db import models

    # Register blueprints
    from .routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app

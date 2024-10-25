from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv, find_dotenv
import os
from app.db.db import db

def create_app():
    # Load environment variables from .env.development if it exists, else from .env
    env_file = find_dotenv('.env.development') or find_dotenv('.env')
    load_dotenv(env_file, override=True)

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

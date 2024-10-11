from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from pathlib import Path
from app.db.db import db

def create_app():
    # Determine the base directory
    base_dir = Path(__file__).resolve().parent.parent

    # Construct paths to .env files
    env_dev_path = base_dir / '.env.development'
    env_prod_path = base_dir / '.env'

    # Load environment variables
    if env_dev_path.exists():
        load_dotenv(dotenv_path=env_dev_path, override=True)
    else:
        load_dotenv(dotenv_path=env_prod_path, override=True)

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
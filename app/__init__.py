# app/__init__.py
from flask import Flask
from dotenv import load_dotenv
import os

def create_app():
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_APP_SECRET_KEY')
    
    from .routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
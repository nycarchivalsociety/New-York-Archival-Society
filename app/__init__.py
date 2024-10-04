# app/__init__.py

from flask import Flask
from flask_login import LoginManager
from app.db.connection import init_db
from app.db.models import User
from dotenv import load_dotenv
import os
import logging

def create_app():
    # Load environment variables from .env file
    load_dotenv()

    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Load configuration settings
    app.config.from_object('app.config.Config')

    # Initialize extensions
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # Initialize database
    init_db(app)

    # Register blueprints
    from .routes.main import main as main_blueprint
    from .routes.auth import auth as auth_blueprint
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint)

    return app

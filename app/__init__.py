# app/__init__.py
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = b'\xf7\xb1}\xf3T"\x8a\x95\xf3{\x01\x0c\x82\xab\x84\xc4\xac\xfe1\x11\x14\x7f\x8b\xb4'
    
    from .routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app

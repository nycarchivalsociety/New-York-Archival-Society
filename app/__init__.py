from flask import Flask

def create_app():
    app = Flask(__name__)

    from .routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .routes.product import product as product_blueprint
    app.register_blueprint(product_blueprint, url_prefix='/products')

    return app

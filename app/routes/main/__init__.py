# In app/routes/main/__init__.py
from flask import Blueprint

main = Blueprint('main', __name__)

from . import views  # Import views after initializing Blueprint

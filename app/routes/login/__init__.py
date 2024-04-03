# In app/routes/items/__init__.py
from flask import Blueprint

login = Blueprint('login', __name__)

from . import views  # Import views after initializing Blueprint

# In app/routes/items/__init__.py
from flask import Blueprint

items = Blueprint('items', __name__)

from . import views  # Import views after initializing Blueprint

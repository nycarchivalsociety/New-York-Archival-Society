# app/routes/main/__init__.py
from flask import Blueprint

auth = Blueprint('auth', __name__)

from . import views

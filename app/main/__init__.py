"""Main blueprint initialization."""

from flask import Blueprint

# Create blueprint
main_bp = Blueprint('main', __name__)

# Import routes after blueprint creation
from app.main import routes

__all__ = ['main_bp']

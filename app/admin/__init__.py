"""Admin blueprint initialization."""

from flask import Blueprint

# Create blueprint
admin_bp = Blueprint('admin', __name__)

# Import routes after blueprint creation
from app.admin import routes

__all__ = ['admin_bp']

"""Authentication blueprint initialization."""

from flask import Blueprint

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Import routes after blueprint creation
from app.auth import routes

__all__ = ['auth_bp']

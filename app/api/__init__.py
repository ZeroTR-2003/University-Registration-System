"""API blueprint initialization."""

from flask import Blueprint

# Create blueprint
api_bp = Blueprint('api', __name__)

# Import routes after blueprint creation to avoid circular imports
from app.api import courses, enrollments, users, auth, grades, transcripts

__all__ = ['api_bp']

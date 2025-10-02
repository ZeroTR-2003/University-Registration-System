"""Student blueprint initialization."""

from flask import Blueprint

# Create blueprint
student_bp = Blueprint('student', __name__)

# Import routes after blueprint creation
from app.student import routes

__all__ = ['student_bp']

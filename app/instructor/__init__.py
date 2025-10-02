"""Instructor blueprint initialization."""

from flask import Blueprint

# Create blueprint
instructor_bp = Blueprint('instructor', __name__)

# Import routes after blueprint creation
from app.instructor import routes

__all__ = ['instructor_bp']

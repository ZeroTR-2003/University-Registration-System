"""Registrar blueprint initialization."""

from flask import Blueprint

registrar_bp = Blueprint('registrar', __name__)

# Import routes after blueprint creation
from app.registrar import routes

__all__ = ['registrar_bp']

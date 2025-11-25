"""WSGI entrypoint that exposes the Flask `app` object for Gunicorn."""

import os
import sys
import logging

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

config_name = os.environ.get('FLASK_CONFIG', 'production')

logger = logging.getLogger(__name__)
try:
    app = create_app(config_name)
    logger.info("WSGI app created successfully")
except Exception:
    logger.exception("Failed to create WSGI app")
    raise

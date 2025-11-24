"""Flask application entry point for deployment."""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from app import create_app
    
    # Get configuration from environment or use default
    config_name = os.environ.get('FLASK_CONFIG', 'development')
    logger.info(f"Creating Flask app in {config_name} mode...")
    
    # Create and export the Flask app
    app = create_app(config_name)
    logger.info("Flask app created successfully!")
    
except Exception as e:
    logger.error(f"Failed to create Flask app: {e}", exc_info=True)
    sys.exit(1)

# Ensure this runs if executed directly (local development)
if __name__ == '__main__':
    try:
        debug_mode = config_name == 'development'
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        
        logger.info(f"Starting University Registration System in {config_name} mode...")
        logger.info(f"Running on http://{host}:{port}")
        
        app.run(host=host, port=port, debug=debug_mode)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)


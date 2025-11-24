"""Flask application entry point for Vercel deployment."""

import os
from app import create_app

# Get configuration from environment or use default
config_name = os.environ.get('FLASK_CONFIG', 'development')

# Create and export the Flask app
app = create_app(config_name)

# Ensure this runs if executed directly (local development)
if __name__ == '__main__':
    debug_mode = config_name == 'development'
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"Starting University Registration System in {config_name} mode...")
    print(f"Running on http://{host}:{port}")
    
    app.run(host=host, port=port, debug=debug_mode)

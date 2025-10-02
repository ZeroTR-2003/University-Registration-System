"""Main entry point for the University Registration System."""

import os
import sys
from app import create_app, db
from app.models import User, Role

# Get configuration from environment or use default
config_name = os.environ.get('FLASK_CONFIG', 'development')
app = create_app(config_name)


@app.cli.command()
def init_db():
    """Initialize the database with tables and default data."""
    db.create_all()
    Role.insert_default_roles()
    print("Database initialized successfully!")


@app.cli.command()
def seed_db():
    """Seed the database with sample data."""
    from seed_data import seed_database
    seed_database()
    print("Database seeded successfully!")


@app.cli.command()
def create_admin():
    """Create an admin user."""
    email = input("Enter admin email: ")
    password = input("Enter admin password: ")
    first_name = input("Enter first name: ")
    last_name = input("Enter last name: ")
    
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        print(f"User with email {email} already exists!")
        return
    
    # Create admin user
    admin_role = Role.query.filter_by(name='Admin').first()
    if not admin_role:
        print("Admin role not found. Run 'flask init-db' first.")
        return
    
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_active=True,
        email_verified=True
    )
    user.set_password(password)
    user.add_role(admin_role)
    
    db.session.add(user)
    db.session.commit()
    
    print(f"Admin user {email} created successfully!")


@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    # Run the application
    debug_mode = config_name == 'development'
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"Starting University Registration System in {config_name} mode...")
    print(f"Running on http://{host}:{port}")
    
    app.run(host=host, port=port, debug=debug_mode)

#!/usr/bin/env python
"""Initialize the database with tables and default data."""

from app import create_app, db
from app.models import User, Role

def init_database():
    """Initialize database with tables and default data."""
    app = create_app('development')
    
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        
        # Insert default roles
        print("Inserting default roles...")
        Role.insert_default_roles()
        
        # Create a default admin user
        admin_email = "admin@university.edu"
        existing_admin = User.query.filter_by(email=admin_email).first()
        
        if not existing_admin:
            print("Creating default admin user...")
            admin = User(
                email=admin_email,
                first_name="Admin",
                last_name="User",
                is_active=True,
                email_verified=True
            )
            admin.set_password("admin123")
            
            admin_role = Role.query.filter_by(name='Admin').first()
            if admin_role:
                admin.roles.append(admin_role)
            
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user created: {admin_email} / admin123")
        else:
            print("Admin user already exists.")
        
        print("Database initialization complete!")

if __name__ == '__main__':
    init_database()

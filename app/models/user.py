"""User and Role models for authentication and authorization."""

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from app.models import db, BaseModel


# Association table for many-to-many relationship between users and roles
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow)
)


class User(BaseModel, UserMixin):
    """User model for authentication."""
    __tablename__ = 'users'
    
    # Basic fields (atomic, no derived data)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    email_verified_at = db.Column(db.DateTime)
    
    # Tracking fields
    last_login = db.Column(db.DateTime)
    last_activity = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    # Contact information
    phone_number = db.Column(db.String(20))
    alternate_email = db.Column(db.String(120))
    
    # Address (normalized, not derived)
    address_line1 = db.Column(db.String(200))
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(100))
    
    # Birth date (not age - age is derived)
    birth_date = db.Column(db.Date)
    
    # Profile picture
    avatar_url = db.Column(db.String(500))
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, back_populates='users', lazy='dynamic')
    student_profile = db.relationship('StudentProfile', foreign_keys='StudentProfile.user_id', back_populates='user', uselist=False, cascade='all, delete-orphan')
    instructor_profile = db.relationship('InstructorProfile', foreign_keys='InstructorProfile.user_id', back_populates='user', uselist=False, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', back_populates='user', cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', back_populates='author')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    @property
    def full_name(self):
        """Computed property for full name."""
        parts = filter(None, [self.first_name, self.middle_name, self.last_name])
        return ' '.join(parts)
    
    @property
    def display_name(self):
        """Display name for UI."""
        return f"{self.first_name} {self.last_name}"
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches."""
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        """Check if user has a specific role."""
        return self.roles.filter(Role.name == role_name).count() > 0
    
    def add_role(self, role):
        """Add a role to the user."""
        if not self.has_role(role.name):
            self.roles.append(role)
    
    def remove_role(self, role):
        """Remove a role from the user."""
        if self.has_role(role.name):
            self.roles.remove(role)
    
    def get_permissions(self):
        """Get all permissions from all roles."""
        permissions = set()
        for role in self.roles:
            permissions.update(role.get_permissions())
        return list(permissions)
    
    def can(self, permission):
        """Check if user has a specific permission."""
        return permission in self.get_permissions()
    
    def is_admin(self):
        """Check if user is an admin."""
        return self.has_role('Admin')
    
    def is_instructor(self):
        """Check if user is an instructor."""
        return self.has_role('Instructor')
    
    def is_student(self):
        """Check if user is a student."""
        return self.has_role('Student')
    
    def is_registrar(self):
        """Check if user is a registrar."""
        return self.has_role('Registrar')
    
    def record_login(self):
        """Record successful login."""
        self.last_login = datetime.utcnow()
        self.login_count += 1
        self.failed_login_count = 0
        
    def record_failed_login(self):
        """Record failed login attempt."""
        self.failed_login_count += 1
        if self.failed_login_count >= 5:
            # Lock account for 30 minutes after 5 failed attempts
            from datetime import timedelta
            self.locked_until = datetime.utcnow() + timedelta(minutes=30)
    
    def is_locked(self):
        """Check if account is locked."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False
    
    def to_dict(self):
        """Convert user to dictionary (excluding sensitive data)."""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'roles': [role.name for role in self.roles.all()] if hasattr(self.roles, 'all') else [role.name for role in self.roles],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

    @property
    def roles_list(self):
        """List of role names for templates."""
        try:
            return [r.name for r in self.roles.all()]
        except Exception:
            return [r.name for r in self.roles]


class Role(BaseModel):
    """Role model for RBAC."""
    __tablename__ = 'roles'
    
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON, default=list)  # List of permission strings
    
    # Relationships
    users = db.relationship('User', secondary=user_roles, back_populates='roles')
    
    # Predefined roles
    ADMIN = 'Admin'
    INSTRUCTOR = 'Instructor'
    STUDENT = 'Student'
    REGISTRAR = 'Registrar'
    
    # Predefined permissions
    PERMISSIONS = {
        'Admin': [
            'manage_users', 'manage_roles', 'manage_courses', 'manage_departments',
            'manage_enrollments', 'view_all_data', 'manage_system', 'generate_reports',
            'override_restrictions', 'manage_announcements', 'manage_settings'
        ],
        'Instructor': [
            'manage_own_courses', 'grade_assignments', 'view_enrolled_students',
            'post_announcements', 'upload_materials', 'manage_assignments',
            'view_course_analytics', 'communicate_students'
        ],
        'Student': [
            'view_courses', 'enroll_courses', 'drop_courses', 'submit_assignments',
            'view_grades', 'view_schedule', 'view_announcements', 'update_profile',
            'view_transcript'
        ],
        'Registrar': [
            'manage_enrollments', 'approve_registrations', 'manage_waitlists',
            'generate_transcripts', 'view_student_records', 'manage_course_sections',
            'handle_prerequisites', 'process_grades', 'override_restrictions'
        ]
    }
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def get_permissions(self):
        """Get permissions for this role."""
        return self.permissions or []
    
    def add_permission(self, permission):
        """Add a permission to this role."""
        if permission not in self.permissions:
            self.permissions = self.permissions or []
            self.permissions.append(permission)
    
    def remove_permission(self, permission):
        """Remove a permission from this role."""
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    @classmethod
    def insert_default_roles(cls):
        """Insert default roles with their permissions."""
        from app.models import db
        for role_name, perms in cls.PERMISSIONS.items():
            role = cls.query.filter_by(name=role_name).first()
            if not role:
                role = cls(name=role_name, permissions=perms)
                role.description = f"Default {role_name} role"
                db.session.add(role)
        db.session.commit()

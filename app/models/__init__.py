"""Database models for the University Registration System."""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy
db = SQLAlchemy()


class BaseModel(db.Model):
    """Base model with common fields."""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def save(self):
        """Save the model to the database."""
        db.session.add(self)
        db.session.commit()
        
    def delete(self):
        """Delete the model from the database."""
        db.session.delete(self)
        db.session.commit()
        
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    @classmethod
    def get_by_id(cls, id):
        """Get model by ID."""
        return cls.query.get(id)


# Import all models to register them with SQLAlchemy
from app.models.user import User, Role, user_roles
from app.models.profile import StudentProfile, InstructorProfile
from app.models.course import Department, Course, CourseSection, CoursePrerequisite
from app.models.enrollment import Enrollment
from app.models.assignment import Assignment, Submission
from app.models.room import Room, Building
from app.models.announcement import Announcement
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.models.media import Media
from app.models.transcript import TranscriptRequest

__all__ = [
    'db',
    'BaseModel',
    'User',
    'Role',
    'user_roles',
    'StudentProfile',
    'InstructorProfile',
    'Department',
    'Course',
    'CourseSection',
    'CoursePrerequisite',
    'Enrollment',
    'Assignment',
    'Submission',
    'Room',
    'Building',
    'Announcement',
    'Notification',
    'AuditLog',
    'Media',
    'TranscriptRequest'
]

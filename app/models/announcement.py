"""Announcement model."""

from app.models import db, BaseModel
from datetime import datetime


class Announcement(BaseModel):
    """Announcement model for course and system announcements."""
    __tablename__ = 'announcements'
    
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'))
    
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    
    # Type and priority
    announcement_type = db.Column(db.String(50), default='General')  # General, Urgent, Assignment, Exam
    priority = db.Column(db.String(20), default='Normal')  # Low, Normal, High, Urgent
    
    # Publishing
    is_published = db.Column(db.Boolean, default=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    # Targeting
    target_roles = db.Column(db.JSON)  # List of role names that should see this
    
    # Attachments
    attachment_urls = db.Column(db.JSON)
    
    # Relationships
    author = db.relationship('User', back_populates='announcements')
    course_section = db.relationship('CourseSection', back_populates='announcements')
    
    def __repr__(self):
        return f'<Announcement {self.title}>'

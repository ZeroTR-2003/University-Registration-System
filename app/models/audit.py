"""Audit log model."""

from app.models import db, BaseModel
from datetime import datetime


class AuditLog(BaseModel):
    """Audit log model for tracking system activities."""
    __tablename__ = 'audit_logs'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    action = db.Column(db.String(100), nullable=False)  # e.g., 'CREATE', 'UPDATE', 'DELETE', 'LOGIN'
    entity_type = db.Column(db.String(50))  # e.g., 'User', 'Course', 'Enrollment'
    entity_id = db.Column(db.Integer)  # ID of the affected entity
    
    # Details
    old_values = db.Column(db.JSON)  # Previous state
    new_values = db.Column(db.JSON)  # New state
    extra_data = db.Column(db.JSON)  # Additional information
    
    # Request information
    ip_address = db.Column(db.String(45))  # Support IPv6
    user_agent = db.Column(db.String(500))
    endpoint = db.Column(db.String(200))  # API endpoint or route
    http_method = db.Column(db.String(10))
    
    # Relationships
    user = db.relationship('User', back_populates='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} by User {self.user_id}>'

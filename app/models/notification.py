"""Notification model."""

from app.models import db, BaseModel
from datetime import datetime


class Notification(BaseModel):
    """Notification model for user notifications."""
    __tablename__ = 'notifications'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    notification_type = db.Column(db.String(50), nullable=False)  # enrollment, grade, announcement, etc.
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Metadata
    payload = db.Column(db.JSON)  # Additional data for the notification
    action_url = db.Column(db.String(500))  # Link to relevant page
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Delivery
    email_sent = db.Column(db.Boolean, default=False)
    sms_sent = db.Column(db.Boolean, default=False)
    push_sent = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = db.relationship('User', back_populates='notifications')
    
    def __repr__(self):
        return f'<Notification {self.notification_type} for User {self.user_id}>'
    
    def mark_as_read(self):
        """Mark notification as read."""
        self.is_read = True
        self.read_at = datetime.utcnow()

"""Media model for file uploads."""

from app.models import db, BaseModel
from datetime import datetime


class Media(BaseModel):
    """Media model for uploaded files."""
    __tablename__ = 'media'
    
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_url = db.Column(db.String(500))
    
    # Metadata
    file_type = db.Column(db.String(50))  # MIME type
    file_size = db.Column(db.Integer)  # Size in bytes
    file_extension = db.Column(db.String(10))
    
    # Usage
    purpose = db.Column(db.String(50))  # assignment, profile_picture, course_material, etc.
    entity_type = db.Column(db.String(50))  # Related entity type
    entity_id = db.Column(db.Integer)  # Related entity ID
    
    # Security
    is_public = db.Column(db.Boolean, default=False)
    access_token = db.Column(db.String(100))  # For secure file access
    
    # Relationships
    owner = db.relationship('User')
    
    def __repr__(self):
        return f'<Media {self.filename}>'

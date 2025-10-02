"""Transcript request model for gating official transcript generation."""

from datetime import datetime
from app.models import db, BaseModel


class TranscriptRequest(BaseModel):
    """Represents a student's request for an official transcript."""
    __tablename__ = 'transcript_requests'

    # The student profile requesting the transcript
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False, index=True)

    # Current status of the request
    status = db.Column(db.String(20), nullable=False, default='Pending')  # Pending, Approved, Rejected, Issued

    # Optional details provided by the student
    purpose = db.Column(db.String(200))
    notes = db.Column(db.Text)

    # Processing details
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    processed_at = db.Column(db.DateTime)
    decision_notes = db.Column(db.Text)

    # Issuance tracking
    issued_at = db.Column(db.DateTime)
    filename = db.Column(db.String(255))

    # Relationships
    student = db.relationship('StudentProfile', backref='transcript_requests')
    processor = db.relationship('User', foreign_keys=[processed_by])

    # Indexes
    __table_args__ = (
        db.Index('idx_transcript_request_status', 'status'),
        db.Index('idx_transcript_request_student_status', 'student_id', 'status'),
    )

    def approve(self, processor_id: int, notes: str = None):
        self.status = 'Approved'
        self.processed_by = processor_id
        self.processed_at = datetime.utcnow()
        self.decision_notes = notes

    def reject(self, processor_id: int, notes: str = None):
        self.status = 'Rejected'
        self.processed_by = processor_id
        self.processed_at = datetime.utcnow()
        self.decision_notes = notes

    def mark_issued(self, filename: str = None):
        self.status = 'Issued'
        self.issued_at = datetime.utcnow()
        if filename:
            self.filename = filename

"""Assignment and Submission models."""

from app.models import db, BaseModel
from datetime import datetime


class Assignment(BaseModel):
    """Assignment model for courses."""
    __tablename__ = 'assignments'
    
    # Assignment details
    course_section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    instructions = db.Column(db.Text)
    
    # Type and weight
    assignment_type = db.Column(db.String(50))  # Homework, Quiz, Exam, Project, etc.
    weight = db.Column(db.Float, default=0)  # Percentage of final grade
    max_points = db.Column(db.Float, nullable=False)
    
    # Dates
    assigned_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    late_submission_deadline = db.Column(db.DateTime)  # Optional extended deadline
    
    # Settings
    allow_late_submission = db.Column(db.Boolean, default=True)
    late_penalty_percentage = db.Column(db.Float, default=10)  # Percentage deducted per day
    allow_resubmission = db.Column(db.Boolean, default=False)
    max_attempts = db.Column(db.Integer, default=1)
    
    # File attachments
    attachment_urls = db.Column(db.JSON)  # List of file URLs
    submission_format = db.Column(db.String(200))  # Expected format (PDF, DOC, etc.)
    max_file_size = db.Column(db.Integer, default=10485760)  # 10MB default
    
    # Visibility
    is_published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime)
    
    # Rubric
    rubric = db.Column(db.JSON)  # Structured rubric data
    
    # Relationships
    course_section = db.relationship('CourseSection', back_populates='assignments')
    submissions = db.relationship('Submission', back_populates='assignment', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Assignment {self.title}>'
    
    def is_overdue(self):
        """Check if assignment is past due."""
        return datetime.utcnow() > self.due_date
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_section_id': self.course_section_id,
            'title': self.title,
            'description': self.description,
            'assignment_type': self.assignment_type,
            'max_points': self.max_points,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'is_published': self.is_published,
            'is_overdue': self.is_overdue()
        }


class Submission(BaseModel):
    """Student submission for assignments."""
    __tablename__ = 'submissions'
    
    # Submission identification
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    
    # Submission details
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    attempt_number = db.Column(db.Integer, default=1)
    
    # Content
    submission_text = db.Column(db.Text)  # For text submissions
    file_urls = db.Column(db.JSON)  # List of submitted file URLs
    
    # Status
    status = db.Column(db.String(50), default='Submitted')  # Submitted, Graded, Returned, Resubmitted
    is_late = db.Column(db.Boolean, default=False)
    late_days = db.Column(db.Integer, default=0)
    
    # Grading
    score = db.Column(db.Float)
    grade_percentage = db.Column(db.Float)
    graded_at = db.Column(db.DateTime)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Feedback
    feedback = db.Column(db.Text)
    rubric_scores = db.Column(db.JSON)  # Scores for each rubric item
    
    # Academic integrity
    plagiarism_score = db.Column(db.Float)  # If using plagiarism detection
    ai_detection_score = db.Column(db.Float)  # If using AI detection
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('assignment_id', 'student_id', 'attempt_number'),
    )
    
    # Relationships
    assignment = db.relationship('Assignment', back_populates='submissions')
    student = db.relationship('StudentProfile', back_populates='submissions')
    grader = db.relationship('User', foreign_keys=[graded_by])
    
    def __repr__(self):
        return f'<Submission Student:{self.student_id} Assignment:{self.assignment_id}>'
    
    def submit(self):
        """Submit the assignment."""
        self.submitted_at = datetime.utcnow()
        self.status = 'submitted'
        
    def grade(self):
        """Mark as graded."""
        self.graded_at = datetime.utcnow()
        self.status = 'graded'
    
    def calculate_final_score(self):
        """Calculate final score with late penalty."""
        if not self.score:
            return 0
        
        final_score = self.score
        
        if self.is_late and self.assignment.allow_late_submission:
            penalty = self.assignment.late_penalty_percentage * self.late_days / 100
            final_score = self.score * (1 - penalty)
        
        return max(0, final_score)
    
    def to_dict(self):
        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'student_id': self.student_id,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'status': self.status,
            'is_late': self.is_late,
            'score': self.score,
            'feedback': self.feedback
        }

"""Profile models for Students and Instructors."""

from app.models import db, BaseModel
from datetime import datetime


class StudentProfile(BaseModel):
    """Student-specific profile information."""
    __tablename__ = 'student_profiles'
    
    # Foreign key to User (1:1 relationship)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    
    # Student-specific fields
    student_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    enrollment_year = db.Column(db.Integer, nullable=False)
    graduation_year = db.Column(db.Integer)
    
    # Academic information
    program = db.Column(db.String(100))  # e.g., "Computer Science"
    degree_type = db.Column(db.String(50))  # e.g., "Bachelor", "Master", "PhD"
    major = db.Column(db.String(100))
    minor = db.Column(db.String(100))
    academic_status = db.Column(db.String(50), default='Active')  # Active, Graduated, Suspended, etc.
    
    # Academic performance (computed from enrollments, but cached for performance)
    total_credits_earned = db.Column(db.Float, default=0)
    total_credits_attempted = db.Column(db.Float, default=0)
    gpa = db.Column(db.Float, default=0.0)
    
    # Advisor information
    advisor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Financial
    tuition_status = db.Column(db.String(50), default='Pending')  # Paid, Pending, Overdue
    scholarship_info = db.Column(db.JSON)
    
    # Additional information
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_relationship = db.Column(db.String(50))
    
    medical_notes = db.Column(db.Text)
    dietary_restrictions = db.Column(db.String(200))
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], back_populates='student_profile')
    advisor = db.relationship('User', foreign_keys=[advisor_id])
    enrollments = db.relationship('Enrollment', back_populates='student', cascade='all, delete-orphan')
    submissions = db.relationship('Submission', back_populates='student', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<StudentProfile {self.student_number}>'
    
    def calculate_gpa(self):
        """Calculate GPA from enrollments."""
        grade_points = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0
        }
        
        total_points = 0
        total_credits = 0
        
        for enrollment in self.enrollments:
            if enrollment.grade and enrollment.grade in grade_points:
                credits = enrollment.course_section.course.credits
                total_points += grade_points[enrollment.grade] * credits
                total_credits += credits
        
        if total_credits > 0:
            self.gpa = round(total_points / total_credits, 2)
            self.total_credits_earned = total_credits
        
        return self.gpa
    
    def can_graduate(self):
        """Check if student meets graduation requirements."""
        # This is a simplified check - real implementation would be more complex
        required_credits = 120  # For bachelor's degree
        min_gpa = 2.0
        
        return (self.total_credits_earned >= required_credits and 
                self.gpa >= min_gpa and 
                self.academic_status == 'Active')
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'student_number': self.student_number,
            'enrollment_year': self.enrollment_year,
            'program': self.program,
            'major': self.major,
            'minor': self.minor,
            'gpa': self.gpa,
            'total_credits': self.total_credits_earned,
            'academic_status': self.academic_status
        }


class InstructorProfile(BaseModel):
    """Instructor-specific profile information."""
    __tablename__ = 'instructor_profiles'
    
    # Foreign key to User (1:1 relationship)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    
    # Instructor-specific fields
    employee_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    
    # Professional information
    title = db.Column(db.String(100))  # e.g., "Professor", "Associate Professor", "Lecturer"
    rank = db.Column(db.String(50))  # Academic rank
    tenure_status = db.Column(db.String(50))  # Tenured, Tenure-track, Non-tenure
    hire_date = db.Column(db.Date, nullable=False)
    
    # Office information
    office_building = db.Column(db.String(100))
    office_room = db.Column(db.String(20))
    office_phone = db.Column(db.String(20))
    office_hours = db.Column(db.JSON)  # Structured office hours data
    
    # Academic qualifications
    highest_degree = db.Column(db.String(100))  # e.g., "PhD in Computer Science"
    degrees = db.Column(db.JSON)  # List of all degrees
    research_interests = db.Column(db.Text)
    bio = db.Column(db.Text)  # Professional biography
    
    # Teaching
    specializations = db.Column(db.JSON)  # List of specialization areas
    max_course_load = db.Column(db.Integer, default=4)  # Max courses per term
    current_course_load = db.Column(db.Integer, default=0)
    
    # Publications and research
    publications = db.Column(db.JSON)  # List of publications
    research_grants = db.Column(db.JSON)  # Active research grants
    
    # Relationships
    user = db.relationship('User', back_populates='instructor_profile')
    department = db.relationship('Department', back_populates='instructors')
    course_sections = db.relationship('CourseSection', back_populates='instructor')
    
    def __repr__(self):
        return f'<InstructorProfile {self.employee_number}>'
    
    def get_current_courses(self, term=None):
        """Get courses currently teaching."""
        from app.models.course import CourseSection
        query = CourseSection.query.filter_by(instructor_id=self.id)
        if term:
            query = query.filter_by(term=term)
        return query.all()
    
    def can_teach_course(self, course):
        """Check if instructor is qualified to teach a course."""
        # Check if course is in instructor's specializations
        if self.specializations and course.code in self.specializations:
            return True
        # Check if department matches
        if self.department_id == course.department_id:
            return True
        return False
    
    def has_capacity(self):
        """Check if instructor can take on more courses."""
        return self.current_course_load < self.max_course_load
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'employee_number': self.employee_number,
            'title': self.title,
            'department_id': self.department_id,
            'office_building': self.office_building,
            'office_room': self.office_room,
            'office_hours': self.office_hours,
            'research_interests': self.research_interests,
            'current_course_load': self.current_course_load
        }

"""Course, Department, and CourseSection models."""

from app.models import db, BaseModel
from datetime import datetime, time
import json


class Department(BaseModel):
    """Department model."""
    __tablename__ = 'departments'
    
    code = db.Column(db.String(10), unique=True, nullable=False)  # e.g., "CS", "MATH"
    name = db.Column(db.String(100), nullable=False)  # e.g., "Computer Science"
    description = db.Column(db.Text)
    
    # Department head
    head_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Contact information
    office_location = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    
    # Relationships
    head = db.relationship('User', foreign_keys=[head_id])
    courses = db.relationship('Course', back_populates='department', cascade='all, delete-orphan')
    instructors = db.relationship('InstructorProfile', back_populates='department')
    
    def __repr__(self):
        return f'<Department {self.code}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'office_location': self.office_location,
            'email': self.email,
            'website': self.website
        }


# Association table for course prerequisites (many-to-many self-referential)
course_prerequisites = db.Table('course_prerequisites',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('prerequisite_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True)
)


class Course(BaseModel):
    """Course catalog model."""
    __tablename__ = 'courses'
    
    # Course identification
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # e.g., "CS101"
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Academic information
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    credits = db.Column(db.Float, nullable=False)  # Credit hours
    level = db.Column(db.String(20))  # Undergraduate, Graduate, Doctoral
    
    # Course details
    syllabus_url = db.Column(db.String(500))
    learning_objectives = db.Column(db.JSON)  # List of objectives
    required_materials = db.Column(db.JSON)  # List of required books/materials
    
    # Restrictions
    max_capacity_default = db.Column(db.Integer, default=30)
    lab_required = db.Column(db.Boolean, default=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    department = db.relationship('Department', back_populates='courses')
    sections = db.relationship('CourseSection', back_populates='course', cascade='all, delete-orphan')
    
    # Self-referential many-to-many for prerequisites
    prerequisites = db.relationship(
        'Course',
        secondary=course_prerequisites,
        primaryjoin='Course.id == course_prerequisites.c.course_id',
        secondaryjoin='Course.id == course_prerequisites.c.prerequisite_id',
        backref='required_for'
    )
    
    def __repr__(self):
        return f'<Course {self.code}: {self.title}>'
    
    def has_prerequisite(self, course):
        """Check if this course has a specific prerequisite."""
        return course in self.prerequisites
    
    def add_prerequisite(self, course):
        """Add a prerequisite course."""
        if not self.has_prerequisite(course):
            self.prerequisites.append(course)
    
    def remove_prerequisite(self, course):
        """Remove a prerequisite course."""
        if self.has_prerequisite(course):
            self.prerequisites.remove(course)
    
    def get_all_prerequisites(self):
        """Get all prerequisites recursively."""
        all_prereqs = set()
        to_process = list(self.prerequisites)
        
        while to_process:
            prereq = to_process.pop(0)
            if prereq not in all_prereqs:
                all_prereqs.add(prereq)
                to_process.extend(prereq.prerequisites)
        
        return list(all_prereqs)
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'title': self.title,
            'description': self.description,
            'department_id': self.department_id,
            'credits': self.credits,
            'level': self.level,
            'prerequisites': [p.code for p in self.prerequisites],
            'is_active': self.is_active
        }


class CoursePrerequisite(BaseModel):
    """Alternative prerequisite model with additional metadata."""
    __tablename__ = 'course_prerequisites_meta'
    
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    prerequisite_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    
    # Additional metadata
    is_mandatory = db.Column(db.Boolean, default=True)  # Required vs recommended
    minimum_grade = db.Column(db.String(5), default='C')  # Minimum grade required
    can_be_concurrent = db.Column(db.Boolean, default=False)  # Can take at same time
    
    # Unique constraint on the combination
    __table_args__ = (
        db.UniqueConstraint('course_id', 'prerequisite_id'),
    )
    
    # Relationships
    course = db.relationship('Course', foreign_keys=[course_id])
    prerequisite = db.relationship('Course', foreign_keys=[prerequisite_id])


class CourseSection(BaseModel):
    """Course section (instance of a course in a specific term)."""
    __tablename__ = 'course_sections'
    
    # Section identification
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    section_code = db.Column(db.String(10), nullable=False)  # e.g., "01", "A", "LAB"
    term = db.Column(db.String(20), nullable=False, index=True)  # e.g., "Fall 2024"
    
    # Instructor
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructor_profiles.id'))
    
    # Capacity
    capacity = db.Column(db.Integer, nullable=False)
    enrolled_count = db.Column(db.Integer, default=0)
    waitlist_capacity = db.Column(db.Integer, default=10)
    waitlist_count = db.Column(db.Integer, default=0)
    
    # Schedule (stored as JSON for flexibility)
    schedule = db.Column(db.JSON)  # e.g., {"days": ["Mon", "Wed"], "start": "10:00", "end": "11:30"}
    
    # Dates
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Location
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))
    delivery_mode = db.Column(db.String(50), default='In-Person')  # In-Person, Online, Hybrid
    
    # Status
    status = db.Column(db.String(50), default='Open')  # Open, Closed, Cancelled
    
    # Additional settings
    allow_audit = db.Column(db.Boolean, default=True)
    require_permission = db.Column(db.Boolean, default=False)
    
    # Unique constraint on course, section, and term
    __table_args__ = (
        db.UniqueConstraint('course_id', 'section_code', 'term'),
    )
    
    # Relationships
    course = db.relationship('Course', back_populates='sections')
    instructor = db.relationship('InstructorProfile', back_populates='course_sections')
    enrollments = db.relationship('Enrollment', back_populates='course_section', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', back_populates='course_section', cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', back_populates='course_section', cascade='all, delete-orphan')
    room = db.relationship('Room', back_populates='course_sections')
    
    @property
    def is_full(self):
        """Check if section is full."""
        return self.enrolled_count >= self.capacity
    
    def promote_from_waitlist(self):
        """Promote next student from waitlist."""
        from app.models.enrollment import Enrollment
        next_student = Enrollment.query.filter_by(
            course_section_id=self.id,
            status='Waitlisted'
        ).order_by(Enrollment.waitlist_position).first()
        
        if next_student and not self.is_full:
            next_student.status = 'Enrolled'
            next_student.enrolled_at = datetime.utcnow()
            next_student.waitlist_position = None
            self.enrolled_count = (self.enrolled_count or 0) + 1
            self.waitlist_count = max(0, (self.waitlist_count or 0) - 1)
    def __repr__(self):
        return f'<CourseSection {self.course.code}-{self.section_code} ({self.term})>'
    
    @property
    def has_waitlist_space(self):
        """Check if waitlist has space."""
        return self.waitlist_count < self.waitlist_capacity
    
    @property
    def available_seats(self):
        """Get number of available seats."""
        return max(0, self.capacity - self.enrolled_count)
    
    def get_meeting_times(self):
        """Parse and return meeting times."""
        if not self.schedule:
            return None
        
        schedule_data = self.schedule if isinstance(self.schedule, dict) else json.loads(self.schedule)
        return schedule_data
    
    def conflicts_with(self, other_section):
        """Check if this section has time conflict with another."""
        if self.term != other_section.term:
            return False
        
        if not self.schedule or not other_section.schedule:
            return False
        
        my_schedule = self.get_meeting_times()
        other_schedule = other_section.get_meeting_times()
        
        # Check for day overlap
        my_days = set(my_schedule.get('days', []))
        other_days = set(other_schedule.get('days', []))
        
        if not my_days.intersection(other_days):
            return False
        
        # Check for time overlap
        my_start = datetime.strptime(my_schedule.get('start', '00:00'), '%H:%M').time()
        my_end = datetime.strptime(my_schedule.get('end', '00:00'), '%H:%M').time()
        other_start = datetime.strptime(other_schedule.get('start', '00:00'), '%H:%M').time()
        other_end = datetime.strptime(other_schedule.get('end', '00:00'), '%H:%M').time()
        
        # Check if times overlap
        return not (my_end <= other_start or other_end <= my_start)
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'course_code': self.course.code,
            'course_title': self.course.title,
            'section_code': self.section_code,
            'term': self.term,
            'instructor_id': self.instructor_id,
            'instructor_name': self.instructor.user.full_name if self.instructor else None,
            'capacity': self.capacity,
            'enrolled_count': self.enrolled_count,
            'available_seats': self.available_seats,
            'schedule': self.schedule,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'delivery_mode': self.delivery_mode,
            'status': self.status
        }

"""Enrollment model with conflict detection and status tracking."""

from app.models import db, BaseModel
from datetime import datetime
from sqlalchemy.orm import synonym
from flask import current_app


class EnrollmentStatus:
    """Compatibility constants for enrollment statuses (string values)."""
    ENROLLED = 'Enrolled'
    WAITLISTED = 'Waitlisted'
    DROPPED = 'Dropped'
    COMPLETED = 'Completed'
    WITHDRAWN = 'Withdrawn'
    FAILED = 'Failed'
    AUDITING = 'Auditing'
    PENDING = 'Pending'


class Enrollment(BaseModel):
    """Enrollment model (many-to-many between students and course sections)."""
    __tablename__ = 'enrollments'
    
    # Composite primary key
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    course_section_id = db.Column(db.Integer, db.ForeignKey('course_sections.id'), nullable=False)
    # Alias to support tests using `section_id`
    section_id = synonym('course_section_id')
    
    # Enrollment details
    status = db.Column(db.String(20), default='Enrolled', nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Grade information (final grade - not age, properly normalized)
    grade = db.Column(db.String(5))  # e.g., "A", "B+", "C-", "F"
    grade_points = db.Column(db.Float)  # Computed from grade
    graded_at = db.Column(db.DateTime)
    grade_mode = db.Column(db.String(20))  # e.g., 'Audit'
    
    # Waitlist information
    waitlist_position = db.Column(db.Integer)
    waitlisted_at = db.Column(db.DateTime)
    
    # Attendance and participation
    attendance_percentage = db.Column(db.Float, default=100.0)
    participation_score = db.Column(db.Float)
    
    # Drop/Withdrawal information
    dropped_at = db.Column(db.DateTime)
    drop_reason = db.Column(db.Text)
    
    # Override information (for admin/registrar overrides)
    override_capacity = db.Column(db.Boolean, default=False)
    override_prerequisites = db.Column(db.Boolean, default=False)
    override_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    override_reason = db.Column(db.Text)
    override_at = db.Column(db.DateTime)
    
    # Notes
    instructor_notes = db.Column(db.Text)
    student_notes = db.Column(db.Text)
    
    # Unique constraint on student and course section
    __table_args__ = (
        db.UniqueConstraint('student_id', 'course_section_id'),
        db.Index('idx_enrollment_status', 'status'),
        db.Index('idx_enrollment_term', 'course_section_id', 'status'),
    )
    
    # Relationships
    student = db.relationship('StudentProfile', back_populates='enrollments')
    course_section = db.relationship('CourseSection', back_populates='enrollments')
    # Read-only alias for tests to access `enrollment.section`
    @property
    def section(self):
        return self.course_section
    
    override_user = db.relationship('User', foreign_keys=[override_by])
    
    def __repr__(self):
        return f"<Enrollment Student:{self.student_id} Section:{self.course_section_id} Status:{self.status}>"
    
    @staticmethod
    def check_prerequisites(student, course):
        """Check if student meets course prerequisites."""
        # Local import to avoid circular dependency
        from app.models.course import CourseSection
        # Get all prerequisites for the course
        prerequisites = course.get_all_prerequisites()
        
        if not prerequisites:
            return True, []
        
        missing_prereqs = []
        
        for prereq in prerequisites:
            # Check if student has completed the prerequisite
            completed = Enrollment.query.filter_by(
                student_id=student.id,
                status='Completed'
            ).join(CourseSection).filter(
                CourseSection.course_id == prereq.id
            ).first()
            
            if not completed:
                missing_prereqs.append(prereq)
            elif completed.grade:
                # Check if grade meets minimum requirement
                grade_values = {'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}
                student_grade_val = grade_values.get(completed.grade[0], 0)
                if student_grade_val < 2:  # Minimum C grade
                    missing_prereqs.append(prereq)
        
        return len(missing_prereqs) == 0, missing_prereqs
    
    @staticmethod
    def check_time_conflicts(student, course_section):
        """Check if course section conflicts with student's current schedule."""
        # Local import to avoid circular dependency
        from app.models.course import CourseSection
        # Get student's current enrollments for the same term
        current_enrollments = Enrollment.query.filter_by(
            student_id=student.id,
            status='Enrolled'
        ).join(CourseSection).filter(
            CourseSection.term == course_section.term
        ).all()
        
        conflicts = []
        for enrollment in current_enrollments:
            if course_section.conflicts_with(enrollment.course_section):
                conflicts.append(enrollment.course_section)
        
        return len(conflicts) == 0, conflicts
    
    @staticmethod
    def check_credit_limit(student, course_section, max_credits=18):
        """Check if enrolling would exceed credit limit."""
        from app.models.course import Course
        
        # Get current term credits
        current_credits = db.session.query(
            db.func.sum(Course.credits)
        ).join(
            CourseSection, Course.id == CourseSection.course_id
        ).join(
            Enrollment, CourseSection.id == Enrollment.course_section_id
        ).filter(
            Enrollment.student_id == student.id,
            Enrollment.status == EnrollmentStatus.ENROLLED,
            CourseSection.term == course_section.term
        ).scalar() or 0
        
        new_credits = course_section.course.credits
        
        total_credits = current_credits + new_credits
        
        return total_credits <= max_credits, total_credits
    
    @staticmethod
    def can_enroll(student, course_section):
        """Comprehensive enrollment eligibility check."""
        errors = []
        warnings = []
        
        # Check if section is full
        if course_section.is_full:
            errors.append("Course section is full")
        
        # Prerequisites check disabled per product decision: allow enrollment regardless of prerequisites
        # (Still visible in data, but no enforcement here.)
        
        # Check time conflicts
        no_conflicts, conflicting_sections = Enrollment.check_time_conflicts(student, course_section)
        if not no_conflicts:
            conflict_names = [f"{s.course.code}-{s.section_code}" for s in conflicting_sections]
            errors.append(f"Time conflict with: {', '.join(conflict_names)}")
        
        # Check credit limit
        within_limit, total_credits = Enrollment.check_credit_limit(student, course_section)
        if not within_limit:
            warnings.append(f"Exceeds credit limit: {total_credits} credits")
        
        # Check if already enrolled
        existing = Enrollment.query.filter_by(
            student_id=student.id,
            course_section_id=course_section.id
        ).first()
        if existing:
            if existing.status == EnrollmentStatus.ENROLLED:
                errors.append("Already enrolled in this section")
            elif existing.status == EnrollmentStatus.WAITLISTED:
                warnings.append("Already on waitlist")
        
        # Check academic standing
        if student.academic_status != 'Active':
            errors.append(f"Academic status is {student.academic_status}")
        
        return len(errors) == 0, errors, warnings
    
    def enroll(self):
        """Process enrollment."""
        # Ensure relationship is loaded if only FK was set
        if not self.course_section and self.course_section_id:
            from app.models.course import CourseSection
            self.course_section = CourseSection.query.get(self.course_section_id)
        if self.course_section is None:
            raise ValueError("course_section must be set before enrolling")
        if self.course_section.is_full:
            self.status = 'Waitlisted'
            self.waitlist_position = (self.course_section.waitlist_count or 0) + 1
            self.waitlisted_at = datetime.utcnow()
            self.course_section.waitlist_count = (self.course_section.waitlist_count or 0) + 1
        else:
            self.status = 'Enrolled'
            self.enrolled_at = datetime.utcnow()
            self.course_section.enrolled_count = (self.course_section.enrolled_count or 0) + 1
    
    
    def drop(self, reason=None):
        """Drop the enrollment."""
        if self.status == 'Enrolled':
            if self.course_section.enrolled_count:
                self.course_section.enrolled_count -= 1
            # Process waitlist if applicable
            self._process_waitlist()
        elif self.status == 'Waitlisted':
            if self.course_section.waitlist_count:
                self.course_section.waitlist_count -= 1
            # Update waitlist positions
            self._update_waitlist_positions()
        
        self.status = 'Dropped'
        self.dropped_at = datetime.utcnow()
        self.drop_reason = reason
    
    def _process_waitlist(self):
        """Process waitlist when a seat becomes available."""
        # Get next student on waitlist
        next_waitlisted = Enrollment.query.filter_by(
            course_section_id=self.course_section_id,
            status='Waitlisted'
        ).order_by(Enrollment.waitlist_position).first()
        
        if next_waitlisted:
            # Move from waitlist to enrolled
            next_waitlisted.status = 'Enrolled'
            next_waitlisted.enrolled_at = datetime.utcnow()
            next_waitlisted.waitlist_position = None
            if self.course_section.waitlist_count:
                self.course_section.waitlist_count -= 1
            self.course_section.enrolled_count = (self.course_section.enrolled_count or 0) + 1
            
            # Notify student about promotion from waitlist
            try:
                from app.models.notification import Notification
                from app import mail
                from flask_mail import Message
                promoted_user = next_waitlisted.student.user if next_waitlisted.student and next_waitlisted.student.user else None
                # Create in-app notification
                if promoted_user:
                    note = Notification(
                        user_id=promoted_user.id,
                        notification_type='enrollment',
                        title='Waitlist Promotion',
                        message=f"You have been enrolled in {self.course_section.course.code}-{self.course_section.section_code} ({self.course_section.term}).",
                        payload={'course_section_id': self.course_section_id}
                    )
                    db.session.add(note)
                    # Attempt email delivery (best-effort)
                    if getattr(promoted_user, 'email', None):
                        msg = Message(
                            subject='Enrollment Update: Waitlist Promotion',
                            recipients=[promoted_user.email],
                            body=(
                                f"Good news! You have been moved from the waitlist to enrolled for "
                                f"{self.course_section.course.code}-{self.course_section.section_code} ({self.course_section.term}).\n"
                                f"Please check your schedule."
                            )
                        )
                        try:
                            mail.send(msg)
                            note.email_sent = True
                        except Exception:
                            pass
            except Exception:
                # Avoid failing enrollment flow due to notification issues
                pass
            
            # Update remaining waitlist positions
            self._update_waitlist_positions()
    
    def _update_waitlist_positions(self):
        """Update waitlist positions after changes."""
        waitlisted = Enrollment.query.filter_by(
            course_section_id=self.course_section_id,
            status='Waitlisted'
        ).order_by(Enrollment.waitlist_position).all()
        
        for i, enrollment in enumerate(waitlisted, 1):
            enrollment.waitlist_position = i
    
    def set_grade(self, grade, grader_id=None):
        """Set the final grade for the enrollment.
        Supports both letter grades and numeric percentage grades.
        """
        grade_points_map = {
            'A+': 4.0, 'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D+': 1.3, 'D': 1.0, 'D-': 0.7,
            'F': 0.0, 'W': None, 'I': None
        }
        
        self.graded_at = datetime.utcnow()
        passing_threshold = 50
        try:
            passing_threshold = int(current_app.config.get('PASSING_GRADE', 50))
        except Exception:
            passing_threshold = 50
        
        # Normalize grade input
        g = grade.strip() if isinstance(grade, str) else grade
        numeric_val = None
        if isinstance(g, (int, float)):
            numeric_val = float(g)
        elif isinstance(g, str):
            try:
                # Strip a trailing percent sign if present
                g_clean = g.replace('%', '').strip()
                numeric_val = float(g_clean)
            except Exception:
                numeric_val = None
        
        if numeric_val is not None:
            # Store as integer percentage if whole number, else as trimmed float string
            self.grade = str(int(numeric_val)) if numeric_val.is_integer() else f"{numeric_val:.1f}"
            # For numeric grades, do not compute grade_points; GPA logic can be extended separately
            self.grade_points = None
            # Update status based on threshold
            if numeric_val >= passing_threshold:
                self.status = 'Completed'
            else:
                self.status = 'Failed'
        else:
            # Treat as letter grade
            self.grade = grade
            self.grade_points = grade_points_map.get(grade)
            # Update status based on grade
            if grade == 'F':
                self.status = 'Failed'
            elif grade == 'W':
                self.status = 'Withdrawn'
            elif grade and grade != 'I':  # I = Incomplete
                self.status = 'Completed'
        
        # Update student's GPA (will consider letter grades; numeric grades currently excluded)
        try:
            self.student.calculate_gpa()
        except Exception:
            pass

    @property
    def numeric_grade(self):
        """Return numeric grade as float if grade is numeric, else None."""
        try:
            return float(str(self.grade).replace('%', '').strip()) if self.grade is not None and str(self.grade).strip() != '' and str(self.grade).replace('%','').strip().replace('.','',1).isdigit() else None
        except Exception:
            return None

    @property
    def derived_status_label(self):
        """Human-readable status derived from grade and status."""
        if self.grade in (None, '', 'I'):
            return 'In Progress'
        # If status explicitly failed/withdrawn, respect it
        if (self.status or '').lower() == 'failed':
            return 'Failed'
        if (self.status or '').lower() == 'withdrawn':
            return 'Withdrawn'
        # Numeric grade handling
        ng = self.numeric_grade
        if ng is not None:
            try:
                threshold = int(current_app.config.get('PASSING_GRADE', 50))
            except Exception:
                threshold = 50
            return 'Completed (Pass)' if ng >= threshold else 'Failed'
        # Letter grade handling
        return 'Failed' if self.grade == 'F' else 'Completed (Pass)'

    @property
    def passed(self):
        """Return True if enrollment is a passing outcome based on grade/value."""
        if not self.grade:
            return False
        if (self.status or '').lower() == 'failed':
            return False
        if (self.status or '').lower() == 'withdrawn':
            return False
        ng = self.numeric_grade
        if ng is not None:
            try:
                threshold = int(current_app.config.get('PASSING_GRADE', 50))
            except Exception:
                threshold = 50
            return ng >= threshold
        return self.grade not in ('F', 'NP')
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'course_section_id': self.course_section_id,
            'course_code': self.course_section.course.code,
            'course_title': self.course_section.course.title,
            'section_code': self.course_section.section_code,
            'term': self.course_section.term,
            'status': self.status,
            'enrolled_at': self.enrolled_at.isoformat() if self.enrolled_at else None,
            'grade': self.grade,
            'waitlist_position': self.waitlist_position,
            'credits': self.course_section.course.credits
        }

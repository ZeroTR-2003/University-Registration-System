"""
Grade Service - Business logic for grade management.
Handles grade entry, validation, GPA calculation, and audit logging.
"""
from typing import List, Tuple, Optional
from datetime import datetime
from app.models import db
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.profile import StudentProfile
from app.models.audit import AuditLog


class GradeService:
    """Service for managing grades and GPA calculations."""
    
    # Valid grade values
    VALID_GRADES = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 
                    'D+', 'D', 'D-', 'F', 'W', 'I', 'P', 'NP']
    
    # Grade point mapping
    GRADE_POINTS = {
        'A+': 4.0, 'A': 4.0, 'A-': 3.7,
        'B+': 3.3, 'B': 3.0, 'B-': 2.7,
        'C+': 2.3, 'C': 2.0, 'C-': 1.7,
        'D+': 1.3, 'D': 1.0, 'D-': 0.7,
        'F': 0.0, 'W': None, 'I': None, 'P': None, 'NP': None
    }
    
    @staticmethod
    def set_grade(enrollment: Enrollment, grade: str, 
                  grader_id: int = None) -> Tuple[bool, List[str]]:
        """
        Set grade for an enrollment.
        
        Args:
            enrollment: Enrollment instance
            grade: Grade value (e.g., 'A', 'B+', etc.)
            grader_id: ID of user setting the grade (instructor/admin)
            
        Returns:
            Tuple of (success, messages)
        """
        messages = []
        
        # Validate grade value (allow numeric percentage as well)
        is_numeric = False
        g = grade.strip() if isinstance(grade, str) else grade
        if isinstance(g, (int, float)):
            is_numeric = True
        elif isinstance(g, str):
            try:
                float(g.replace('%', '').strip())
                is_numeric = True
            except Exception:
                is_numeric = False
        if not is_numeric and grade not in GradeService.VALID_GRADES:
            messages.append(f"Invalid grade: {grade}")
            return False, messages
        
        # Check if enrollment is in a gradable status
        if enrollment.status not in ['Enrolled', 'Completed']:
            messages.append("Cannot grade: Student is not enrolled or completed")
            return False, messages
        
        # Record old grade for audit
        old_grade = enrollment.grade
        
        try:
            # Set the grade using enrollment's method
            enrollment.set_grade(grade, grader_id)
            # Recalculate student's GPA
            try:
                enrollment.student.calculate_gpa()
            except Exception:
                pass
            db.session.commit()
        except Exception as ex:
            db.session.rollback()
            messages.append('Failed to set grade due to an unexpected error. Please try again.')
            return False, messages
        
        # Notify student about grade
        try:
            from app.models.notification import Notification
            if enrollment.student and enrollment.student.user:
                # Include pass/fail in message if determinable
                outcome = None
                try:
                    outcome = 'Passed' if enrollment.passed else ('Failed' if enrollment.derived_status_label == 'Failed' else None)
                except Exception:
                    outcome = None
                outcome_text = f" ({outcome})" if outcome else ""
                notification = Notification(
                    user_id=enrollment.student.user_id,
                    notification_type='grade',
                    title='Grade Posted',
                    message=f"Your grade for {enrollment.course_section.course.code}-{enrollment.course_section.section_code} has been posted: {grade}{outcome_text}",
                    payload={'enrollment_id': enrollment.id, 'grade': grade}
                )
                db.session.add(notification)
                db.session.commit()
        except Exception:
            # Don't fail grading if notification fails
            pass
        
        # Create audit message and log
        action_msg = None
        if old_grade:
            action_msg = f"Grade changed from {old_grade} to {grade}"
            messages.append(action_msg)
        else:
            action_msg = f"Grade set to {grade}"
            messages.append(action_msg)

        try:
            audit = AuditLog(
                user_id=grader_id or 0,
                action='GRADE_CHANGE',
                entity_type='Enrollment',
                entity_id=enrollment.id,
                old_values={'grade': old_grade} if old_grade else None,
                new_values={'grade': grade, 'status': enrollment.status},
            )
            db.session.add(audit)
            db.session.commit()
        except Exception:
            # Avoid breaking grading flow due to audit issues
            db.session.rollback()
        
        return True, messages
    
    @staticmethod
    def bulk_set_grades(enrollments_grades: List[Tuple[Enrollment, str]], 
                       grader_id: int = None) -> Tuple[int, int, List[str]]:
        """
        Set grades for multiple enrollments.
        
        Args:
            enrollments_grades: List of (enrollment, grade) tuples
            grader_id: ID of user setting grades
            
        Returns:
            Tuple of (success_count, fail_count, messages)
        """
        success_count = 0
        fail_count = 0
        messages = []
        
        for enrollment, grade in enrollments_grades:
            success, msgs = GradeService.set_grade(enrollment, grade, grader_id)
            if success:
                success_count += 1
            else:
                fail_count += 1
                messages.extend(msgs)
        
        messages.insert(0, f"Grades set: {success_count} success, {fail_count} failed")
        return success_count, fail_count, messages
    
    @staticmethod
    def get_section_roster(section_id: int) -> List[Enrollment]:
        """
        Get all enrolled students for a section.
        
        Args:
            section_id: CourseSection ID
            
        Returns:
            List of Enrollment objects
        """
        enrollments = Enrollment.query.filter_by(
            course_section_id=section_id
        ).filter(
            Enrollment.status.in_(['Enrolled', 'Completed'])
        ).join(StudentProfile).order_by(
            StudentProfile.student_number
        ).all()
        
        return enrollments
    
    @staticmethod
    def get_gradable_enrollments(section_id: int) -> List[Enrollment]:
        """
        Get enrollments that can be graded (enrolled or completed).
        
        Args:
            section_id: CourseSection ID
            
        Returns:
            List of Enrollment objects
        """
        enrollments = Enrollment.query.filter_by(
            course_section_id=section_id
        ).filter(
            Enrollment.status.in_(['Enrolled', 'Completed'])
        ).join(StudentProfile).order_by(
            StudentProfile.student_number
        ).all()
        
        return enrollments
    
    @staticmethod
    def get_student_grades(student_profile: StudentProfile, 
                          term: str = None) -> List[Enrollment]:
        """
        Get all graded enrollments for a student.
        
        Args:
            student_profile: StudentProfile instance
            term: Optional term filter
            
        Returns:
            List of Enrollment objects with grades
        """
        from app.models.course import CourseSection
        
        query = Enrollment.query.filter_by(
            student_id=student_profile.id
        ).filter(
            Enrollment.grade.isnot(None)
        )
        
        if term:
            query = query.join(CourseSection).filter(CourseSection.term == term)
        
        query = query.join(CourseSection).order_by(
            CourseSection.term.desc(),
            CourseSection.id
        )
        
        return query.all()
    
    @staticmethod
    def calculate_term_gpa(student_profile: StudentProfile, term: str) -> float:
        """
        Calculate GPA for a specific term.
        
        Args:
            student_profile: StudentProfile instance
            term: Term (e.g., "Spring 2025")
            
        Returns:
            Term GPA as float
        """
        from app.models.course import CourseSection
        
        enrollments = Enrollment.query.filter_by(
            student_id=student_profile.id
        ).join(CourseSection).filter(
            CourseSection.term == term,
            Enrollment.grade.isnot(None)
        ).all()
        
        total_points = 0
        total_credits = 0
        
        for enrollment in enrollments:
            if enrollment.grade in GradeService.GRADE_POINTS:
                points = GradeService.GRADE_POINTS[enrollment.grade]
                if points is not None:  # Exclude W, I, P, NP
                    credits = enrollment.course_section.course.credits
                    total_points += points * credits
                    total_credits += credits
        
        if total_credits > 0:
            return round(total_points / total_credits, 2)
        return 0.0
    
    @staticmethod
    def get_grade_distribution(section_id: int) -> dict:
        """
        Get grade distribution for a section.
        
        Args:
            section_id: CourseSection ID
            
        Returns:
            Dictionary with grade counts
        """
        enrollments = Enrollment.query.filter_by(
            course_section_id=section_id
        ).filter(
            Enrollment.grade.isnot(None)
        ).all()
        
        distribution = {}
        for enrollment in enrollments:
            grade = enrollment.grade
            distribution[grade] = distribution.get(grade, 0) + 1
        
        return distribution
    
    @staticmethod
    def validate_grade(grade: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a grade value.
        
        Args:
            grade: Grade to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not grade:
            return False, "Grade cannot be empty"
        
        if grade not in GradeService.VALID_GRADES:
            return False, f"Invalid grade: {grade}. Valid grades: {', '.join(GradeService.VALID_GRADES)}"
        
        return True, None
    
    @staticmethod
    def can_change_grade(enrollment: Enrollment, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if a user can change a grade.
        
        Args:
            enrollment: Enrollment instance
            user_id: User attempting to change grade
            
        Returns:
            Tuple of (can_change, reason)
        """
        # Check if section instructor
        if enrollment.course_section.instructor_id == user_id:
            return True, None
        
        # Check if admin/registrar (would need to check user roles)
        # For now, allow instructor only
        return False, "Only the instructor can change grades"
    
    @staticmethod
    def get_grading_summary(section_id: int) -> dict:
        """
        Get summary of grading progress for a section.
        
        Args:
            section_id: CourseSection ID
            
        Returns:
            Dictionary with grading statistics
        """
        enrollments = Enrollment.query.filter_by(
            course_section_id=section_id
        ).filter(
            Enrollment.status.in_([EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED])
        ).all()
        
        total = len(enrollments)
        graded = sum(1 for e in enrollments if e.grade)
        ungraded = total - graded
        
        return {
            'total_students': total,
            'graded': graded,
            'ungraded': ungraded,
            'percentage_complete': round((graded / total * 100) if total > 0 else 0, 1)
        }

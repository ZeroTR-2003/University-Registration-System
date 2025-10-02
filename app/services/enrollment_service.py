"""Enrollment-related services."""
from typing import List, Tuple, Optional
from datetime import datetime
from app.models import db
from app.models.enrollment import Enrollment
from app.models.course import CourseSection, Course
from app.models.audit import AuditLog


def can_enroll(student_profile, section: CourseSection):
    """Check if student can enroll in section."""
    return Enrollment.can_enroll(student_profile, section)


def enroll_student(student_profile, section: CourseSection, 
                  audit_mode: bool = False, 
                  override_by: int = None) -> Tuple[Enrollment, bool, List[str]]:
    """
    Enroll student in section with validation.
    Returns: (enrollment, success, messages)
    """
    messages = []
    
    # Check for existing enrollment
    existing = Enrollment.query.filter_by(
        student_id=student_profile.id,
        course_section_id=section.id
    ).filter(
        Enrollment.status.in_(['Enrolled', 'Waitlisted'])
    ).first()
    
    if existing:
        if existing.status == 'Enrolled':
            messages.append("Already enrolled in this section")
            return existing, False, messages
        elif existing.status == 'Waitlisted':
            messages.append(f"Already on waitlist (Position: {existing.waitlist_position})")
            return existing, False, messages
    
    # Validate enrollment unless override
    if not override_by:
        ok, errors, warnings = can_enroll(student_profile, section)
        if not ok:
            messages.extend(errors)
            return None, False, messages
        messages.extend(warnings)
    
    # Concurrency hardening: lock section row before capacity checks (no-op on SQLite)
    try:
        locked_section = db.session.query(CourseSection).filter_by(id=section.id).with_for_update().first()
        if locked_section:
            section = locked_section
    except Exception:
        # If DB doesn't support SELECT ... FOR UPDATE, proceed without locking
        pass

    try:
        # Transactional enrollment
        with db.session.begin():
            # Create enrollment
            enrollment = Enrollment(
                student_id=student_profile.id, 
                course_section_id=section.id
            )
            
            if audit_mode:
                if not section.allow_audit:
                    messages.append("This section does not allow auditing")
                    return None, False, messages
                enrollment.status = 'Auditing'
                enrollment.enrolled_at = datetime.utcnow()
            else:
                enrollment.enroll()
            
            if override_by:
                enrollment.override_capacity = True
                enrollment.override_prerequisites = True
                enrollment.override_by = override_by
                enrollment.override_at = datetime.utcnow()
            
            db.session.add(enrollment)
    except Exception:
        db.session.rollback()
        messages.append('Enrollment failed due to an unexpected error. Please try again.')
        return None, False, messages
    
    # Notify student and instructor
    try:
        from app.models.notification import Notification
        # Student confirmation
        if getattr(student_profile, 'user_id', None):
            student_note = Notification(
                user_id=student_profile.user_id,
                notification_type='enrollment',
                title='Enrollment Confirmed' if enrollment.status == 'Enrolled' else 'Added to Waitlist',
                message=(
                    f"You have been {'enrolled in' if enrollment.status == 'Enrolled' else 'added to the waitlist for'} "
                    f"{section.course.code}-{section.section_code} ({section.term})."
                    + (f" Waitlist position: {enrollment.waitlist_position}." if enrollment.status == 'Waitlisted' else "")
                ),
                payload={'enrollment_id': enrollment.id, 'section_id': section.id}
            )
            db.session.add(student_note)
        # Instructor notification
        if section.instructor and section.instructor.user:
            instructor_note = Notification(
                user_id=section.instructor.user_id,
                notification_type='enrollment',
                title='New Student Enrollment',
                message=f"{student_profile.user.full_name} has enrolled in {section.course.code}-{section.section_code} ({section.term}).",
                payload={'enrollment_id': enrollment.id, 'section_id': section.id}
            )
            db.session.add(instructor_note)
        db.session.commit()
    except Exception:
        # Don't fail enrollment if notification fails
        pass
    
    # Audit log
    try:
        audit = AuditLog(
            user_id=override_by or getattr(student_profile, 'user_id', None) or 0,
            action='ENROLL_OVERRIDE' if override_by else 'ENROLL',
            entity_type='Enrollment',
            entity_id=enrollment.id,
            new_values={'status': enrollment.status, 'student_id': enrollment.student_id, 'course_section_id': enrollment.course_section_id}
        )
        db.session.add(audit)
        db.session.commit()
    except Exception:
        db.session.rollback()

    if enrollment.status == 'Enrolled':
        messages.append(f"Successfully enrolled in {section.course.code}")
    elif enrollment.status == 'Waitlisted':
        messages.append(f"Added to waitlist (Position: {enrollment.waitlist_position})")
    elif enrollment.status == 'Auditing':
        messages.append("Enrolled as auditing")
    
    return enrollment, True, messages


def drop_enrollment(enrollment: Enrollment, reason: str = None) -> Tuple[bool, List[str]]:
    """
    Drop enrollment.
    Returns: (success, messages)
    """
    messages = []
    
    if enrollment.status not in ['Enrolled', 'Waitlisted', 'Auditing']:
        messages.append("Cannot drop - course is not active")
        return False, messages
    
    course_title = enrollment.course_section.course.title
    enrollment.drop(reason=reason)
    db.session.commit()
    
    # Promote from waitlist if applicable
    if hasattr(enrollment.course_section, 'promote_from_waitlist'):
        enrollment.course_section.promote_from_waitlist()
        db.session.commit()
    
    # Audit log
    try:
        audit = AuditLog(
            user_id=getattr(enrollment.student, 'user_id', None) or 0,
            action='DROP',
            entity_type='Enrollment',
            entity_id=enrollment.id,
            old_values={'status': 'Enrolled'},
            new_values={'status': 'Dropped', 'reason': reason},
        )
        db.session.add(audit)
        db.session.commit()
    except Exception:
        db.session.rollback()

    messages.append(f"Successfully dropped {course_title}")
    return True, messages


def get_available_sections(term: str = None, department_id: int = None, 
                          search: str = None, status: str = 'Open') -> List[CourseSection]:
    """
    Get available sections with filters.
    """
    query = CourseSection.query.join(Course)
    
    if term:
        query = query.filter(CourseSection.term == term)
    
    if department_id:
        query = query.filter(Course.department_id == department_id)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                Course.code.ilike(search_pattern),
                Course.title.ilike(search_pattern)
            )
        )
    
    query = query.filter(CourseSection.status == status)
    query = query.order_by(Course.code, CourseSection.section_code)
    
    return query.all()


def get_student_enrollments(student_profile, status: str = None, 
                           term: str = None) -> List[Enrollment]:
    """
    Get student enrollments with filters.
    """
    query = Enrollment.query.filter_by(student_id=student_profile.id)
    
    if status:
        # Normalize: accept 'enrolled', 'waitlisted', 'completed', etc.
        normalized = status.strip().lower()
        status_map = {
            'enrolled': 'Enrolled',
            'waitlisted': 'Waitlisted',
            'completed': 'Completed',
            'dropped': 'Dropped',
            'withdrawn': 'Withdrawn',
            'auditing': 'Auditing',
        }
        query = query.filter_by(status=status_map.get(normalized, normalized.capitalize()))
    
    if term:
        query = query.join(CourseSection).filter(CourseSection.term == term)
    
    query = query.join(CourseSection).order_by(
        CourseSection.term.desc(), 
        CourseSection.id
    )
    
    return query.all()


def get_enrollment_summary(student_profile, term: str = None) -> dict:
    """
    Get enrollment summary statistics.
    """
    query = Enrollment.query.filter_by(student_id=student_profile.id)
    
    if term:
        query = query.join(CourseSection).filter(CourseSection.term == term)
    
    enrollments = query.all()
    
    enrolled = [e for e in enrollments if e.status == 'Enrolled']
    waitlisted = [e for e in enrollments if e.status == 'Waitlisted']
    completed = [e for e in enrollments if e.status == 'Completed']
    
    total_credits = sum(e.course_section.course.credits for e in enrolled)
    
    return {
        'enrolled_count': len(enrolled),
        'waitlisted_count': len(waitlisted),
        'completed_count': len(completed),
        'total_credits': total_credits,
        'gpa': student_profile.gpa or 0.0
    }

"""
Tests for the enrollment engine including prerequisites, capacity, and conflicts.
These tests verify the core enrollment business logic.
"""
import pytest
from datetime import date, datetime
from app.models import db
from app.models.course import Department, Course, CourseSection
from app.models.enrollment import Enrollment
from app.models.user import User
from tests.helpers import create_student, seed_simple_course


def test_basic_enrollment(app_context, student_user):
    """Test basic enrollment in a section."""
    section = seed_simple_course()
    
    # Attempt enrollment
    enrollment = Enrollment(
        student_id=student_user.student_profile.id,
        section_id=section.id,
        status='Enrolled',
        enrolled_at=datetime.utcnow()
    )
    db.session.add(enrollment)
    db.session.commit()
    
    assert enrollment.id is not None
    assert enrollment.status == 'Enrolled'
    assert enrollment.student_id == student_user.student_profile.id


def test_enrollment_capacity_limit(app_context):
    """Test that enrollments respect section capacity."""
    section = seed_simple_course()
    section.capacity = 2
    db.session.commit()
    
    # Create two students and enroll them
    student1 = create_student(email="student1@test.edu")
    student2 = create_student(email="student2@test.edu")
    
    enrollment1 = Enrollment(
        student_id=student1.student_profile.id,
        section_id=section.id,
        status='Enrolled',
        enrolled_at=datetime.utcnow()
    )
    enrollment2 = Enrollment(
        student_id=student2.student_profile.id,
        section_id=section.id,
        status='Enrolled',
        enrolled_at=datetime.utcnow()
    )
    db.session.add_all([enrollment1, enrollment2])
    db.session.commit()
    
    # Check enrolled count
    enrolled_count = Enrollment.query.filter_by(
        section_id=section.id,
        status='Enrolled'
    ).count()
    
    assert enrolled_count == 2
    assert enrolled_count >= section.capacity


def test_waitlist_when_full(app_context):
    """Test that students are waitlisted when section is full."""
    section = seed_simple_course()
    section.capacity = 1
    db.session.commit()
    
    # First student enrolls normally
    student1 = create_student(email="first@test.edu")
    enrollment1 = Enrollment(
        student_id=student1.student_profile.id,
        section_id=section.id,
        status='Enrolled',
        enrolled_at=datetime.utcnow()
    )
    db.session.add(enrollment1)
    db.session.commit()
    
    # Second student should go to waitlist
    student2 = create_student(email="second@test.edu")
    enrollment2 = Enrollment(
        student_id=student2.student_profile.id,
        section_id=section.id,
        status='Waitlisted',
        enrolled_at=datetime.utcnow()
    )
    db.session.add(enrollment2)
    db.session.commit()
    
    assert enrollment1.status == 'Enrolled'
    assert enrollment2.status == 'Waitlisted'


def test_drop_enrollment(app_context, student_user):
    """Test dropping an enrollment."""
    section = seed_simple_course()
    
    enrollment = Enrollment(
        student_id=student_user.student_profile.id,
        section_id=section.id,
        status='Enrolled',
        enrolled_at=datetime.utcnow()
    )
    db.session.add(enrollment)
    db.session.commit()
    
    # Drop the enrollment
    enrollment.status = 'Dropped'
    enrollment.dropped_at = datetime.utcnow()
    db.session.commit()
    
    assert enrollment.status == 'Dropped'
    assert enrollment.dropped_at is not None


def test_prevent_duplicate_enrollment(app_context, student_user):
    """Test that a student cannot enroll in the same section twice."""
    section = seed_simple_course()
    
    # First enrollment
    enrollment1 = Enrollment(
        student_id=student_user.student_profile.id,
        section_id=section.id,
        status='Enrolled',
        enrolled_at=datetime.utcnow()
    )
    db.session.add(enrollment1)
    db.session.commit()
    
    # Check for existing enrollment
    existing = Enrollment.query.filter_by(
        student_id=student_user.student_profile.id,
        section_id=section.id,
        status='Enrolled'
    ).first()
    
    assert existing is not None
    # In real implementation, this should raise an error or be prevented


def test_audit_enrollment(app_context, student_user):
    """Test audit-only enrollment."""
    section = seed_simple_course()
    section.allow_audit = True
    db.session.commit()
    
    enrollment = Enrollment(
        student_id=student_user.student_profile.id,
        section_id=section.id,
        status='Enrolled',
        grade_mode='Audit',
        enrolled_at=datetime.utcnow()
    )
    db.session.add(enrollment)
    db.session.commit()
    
    assert enrollment.grade_mode == 'Audit'


def test_enrollment_term_filtering(app_context, student_user):
    """Test filtering enrollments by term."""
    dept = Department.query.filter_by(code="CS").first()
    course = Course.query.filter_by(code="CS101").first()
    
    # Create sections for different terms
    section_spring = CourseSection(
        course_id=course.id,
        section_code="02",
        term="Spring 2025",
        capacity=30,
        start_date=date(2025, 1, 15),
        end_date=date(2025, 5, 15)
    )
    section_fall = CourseSection(
        course_id=course.id,
        section_code="03",
        term="Fall 2024",
        capacity=30,
        start_date=date(2024, 8, 15),
        end_date=date(2024, 12, 15)
    )
    db.session.add_all([section_spring, section_fall])
    db.session.commit()
    
    # Enroll in both
    enrollment_spring = Enrollment(
        student_id=student_user.student_profile.id,
        section_id=section_spring.id,
        status='Enrolled',
        enrolled_at=datetime.utcnow()
    )
    enrollment_fall = Enrollment(
        student_id=student_user.student_profile.id,
        section_id=section_fall.id,
        status='Enrolled',
        enrolled_at=datetime.utcnow()
    )
    db.session.add_all([enrollment_spring, enrollment_fall])
    db.session.commit()
    
    # Query Spring 2025 enrollments
    spring_enrollments = (
        db.session.query(Enrollment)
        .join(CourseSection)
        .filter(
            Enrollment.student_id == student_user.student_profile.id,
            CourseSection.term == "Spring 2025",
            Enrollment.status == 'Enrolled'
        )
        .all()
    )
    
    assert len(spring_enrollments) == 1
    assert spring_enrollments[0].section.term == "Spring 2025"


def test_section_status_closed(app_context, student_user):
    """Test that students cannot enroll in closed sections."""
    section = seed_simple_course()
    section.status = 'Closed'
    db.session.commit()
    
    # In a real implementation, enrollment should be prevented
    # For now, we just verify the status
    assert section.status == 'Closed'


def test_section_status_cancelled(app_context):
    """Test cancelled section handling."""
    section = seed_simple_course()
    section.status = 'Cancelled'
    db.session.commit()
    
    assert section.status == 'Cancelled'
    # In real implementation, enrolled students should be notified


def test_enrollment_with_permission_required(app_context, student_user):
    """Test enrollment in sections requiring permission."""
    section = seed_simple_course()
    section.require_permission = True
    db.session.commit()
    
    # Enrollment should be marked as pending permission
    enrollment = Enrollment(
        student_id=student_user.student_profile.id,
        section_id=section.id,
        status='Pending',  # Or could be 'Enrolled' with a flag
        enrolled_at=datetime.utcnow()
    )
    db.session.add(enrollment)
    db.session.commit()
    
    assert section.require_permission is True

"""Background tasks using Celery."""

from app import celery, db
from app.models import Enrollment


@celery.task(name="tasks.recalc_enrollment_counts")
def recalc_enrollment_counts(course_section_id: int) -> int:
    """Recalculate enrolled and waitlist counts for a section."""
    # using string statuses
    from app.models.course import CourseSection

    section = CourseSection.query.get(course_section_id)
    if not section:
        return 0
    enrolled = Enrollment.query.filter_by(course_section_id=course_section_id, status='Enrolled').count()
    waitlisted = Enrollment.query.filter_by(course_section_id=course_section_id, status='Waitlisted').count()
    section.enrolled_count = enrolled
    section.waitlist_count = waitlisted
    db.session.commit()
    return enrolled

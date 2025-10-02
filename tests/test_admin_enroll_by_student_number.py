import pytest
from app.models import db
from tests.helpers import create_student, seed_simple_course


def test_admin_enroll_by_student_number(authenticated_admin_client, app_context):
    # Create a student and a course section
    student = create_student("admin-enroll@test.edu")
    section = seed_simple_course()

    # Post to admin enroll by student number using course code
    resp = authenticated_admin_client.post(
        "/admin/enroll_by_student_number",
        data={
            "student_number": student.student_profile.student_number,
            "course_identifier": section.course.code,
            "section_id": section.id,
            "csrf_token": "whatever",
        },
        follow_redirects=False,
    )
    # Expect a redirect back to course detail
    assert resp.status_code in (302, 303)

    # Enrollment should exist
    from app.models.enrollment import Enrollment
    e = db.session.query(Enrollment).filter_by(student_id=student.student_profile.id, course_section_id=section.id).first()
    assert e is not None

    # Notification should be created for the student
    from app.models.notification import Notification
    note_count = Notification.query.filter_by(user_id=student.id).count()
    assert note_count >= 1

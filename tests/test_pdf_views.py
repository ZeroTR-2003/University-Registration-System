import pytest
from app.models import db
from tests.helpers import create_student, create_instructor, seed_simple_course, login_user


def test_student_registration_proof_pdf_view(authenticated_student_client, app_context):
    # No enrollments required; PDF should still generate with "No courses enrolled"
    resp = authenticated_student_client.get('/student/registration-proof')
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type', '').startswith('application/pdf')
    assert resp.data[:4] == b'%PDF'


def test_instructor_roster_pdf_view(authenticated_instructor_client, app_context):
    # Seed a section and assign to instructor
    from app.models.profile import InstructorProfile
    from app.models.course import CourseSection
    instr = InstructorProfile.query.first()
    section = seed_simple_course()
    section.instructor_id = instr.id
    db.session.commit()

    resp = authenticated_instructor_client.get(f'/instructor/roster_pdf/{section.id}')
    assert resp.status_code == 200
    assert resp.headers.get('Content-Type', '').startswith('application/pdf')
    assert resp.data[:4] == b'%PDF'

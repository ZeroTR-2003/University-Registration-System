from datetime import date
from app.models import db
from app.models.enrollment import Enrollment
from tests.helpers import create_instructor, create_student, seed_simple_course


def _api_login(client, email, password):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200
    return r.get_json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_grades_api_set_and_roster(client, app_context):
    # Seed a section and assign an instructor to it
    section = seed_simple_course()
    instructor_user = create_instructor("gr_instructor@test.edu")
    section.instructor_id = instructor_user.instructor_profile.id
    db.session.commit()

    # Enroll a student
    student_user = create_student("gr_student@test.edu")
    e = Enrollment(student_id=student_user.student_profile.id, course_section_id=section.id)
    e.enroll()
    db.session.add(e)
    db.session.commit()

    # Login as instructor
    token = _api_login(client, instructor_user.email, "instructorpass123")

    # Set grade
    resp = client.post(
        f"/api/v1/enrollments/{e.id}/grade",
        json={"grade": "A"},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["enrollment"]["grade"] == "A"

    # Roster endpoint should return the student
    resp = client.get(f"/api/v1/sections/{section.id}/roster", headers=_auth(token))
    assert resp.status_code == 200
    roster = resp.get_json()
    assert isinstance(roster, list)
    assert any(row["student_id"] == student_user.student_profile.id for row in roster)

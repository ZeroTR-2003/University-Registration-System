from io import BytesIO
from datetime import date
from app.models import db
from app.models.enrollment import Enrollment
from tests.helpers import create_student, create_registrar, seed_simple_course


def _api_login(client, email, password):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200
    return r.get_json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_transcript_me_pdf(client, app_context):
    # Seed data: course and a graded enrollment for the student
    section = seed_simple_course()
    student_user = create_student("transcript_me@test.edu")

    e = Enrollment(student_id=student_user.student_profile.id, course_section_id=section.id)
    e.enroll()
    e.set_grade('A')
    db.session.add(e)
    db.session.commit()

    token = _api_login(client, student_user.email, "pass12345")
    resp = client.get("/api/v1/transcripts/me", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.headers.get("Content-Type", "").startswith("application/pdf")
    # PDF magic header
    assert resp.data[:4] == b"%PDF"


def test_transcript_official_by_registrar(client, app_context):
    # Seed
    section = seed_simple_course()
    student_user = create_student("transcript_reg@test.edu")
    e = Enrollment(student_id=student_user.student_profile.id, course_section_id=section.id)
    e.enroll()
    e.set_grade('B+')
    db.session.add(e)
    db.session.commit()

    # Registrar downloads official transcript
    registrar = create_registrar("regx@test.edu")
    token = _api_login(client, registrar.email, "registrarpass123")

    resp = client.get(f"/api/v1/transcripts/{student_user.id}?official=true", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.headers.get("Content-Type", "").startswith("application/pdf")
    assert resp.data[:4] == b"%PDF"
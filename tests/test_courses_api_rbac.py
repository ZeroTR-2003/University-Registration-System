from app.models import db
from app.models.course import Department, Course
from tests.helpers import create_admin, create_instructor, create_student


def _api_login(client, email, password):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200
    return r.get_json()["access_token"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_course_crud_rbac(client, app_context):
    # Seed department
    dep = Department(code="CS", name="Computer Science")
    db.session.add(dep)
    db.session.commit()

    # Create users
    admin = create_admin()
    instructor = create_instructor()
    student = create_student("student_rbac@test.edu")

    # Login to get tokens
    admin_token = _api_login(client, admin.email, "adminpass123")
    instr_token = _api_login(client, instructor.email, "instructorpass123")
    stud_token = _api_login(client, student.email, "pass12345")

    # Student cannot create course
    resp = client.post(
        "/api/v1/courses",
        json={
            "code": "CS200",
            "title": "Systems",
            "department_id": dep.id,
            "credits": 4.0,
        },
        headers=_auth_header(stud_token),
    )
    assert resp.status_code == 403

    # Instructor can create
    resp = client.post(
        "/api/v1/courses",
        json={
            "code": "CS201",
            "title": "Algorithms",
            "department_id": dep.id,
            "credits": 3.0,
        },
        headers=_auth_header(instr_token),
    )
    assert resp.status_code == 201
    course_id = resp.get_json()["id"]

    # Admin can update
    resp = client.put(
        f"/api/v1/courses/{course_id}",
        json={"title": "Advanced Algorithms"},
        headers=_auth_header(admin_token),
    )
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Advanced Algorithms"

    # Instructor cannot delete
    resp = client.delete(
        f"/api/v1/courses/{course_id}", headers=_auth_header(instr_token)
    )
    assert resp.status_code == 403

    # Admin can delete
    resp = client.delete(
        f"/api/v1/courses/{course_id}", headers=_auth_header(admin_token)
    )
    assert resp.status_code == 204

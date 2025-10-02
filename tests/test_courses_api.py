from app.models import db
from app.models.course import Department, Course


def test_courses_list_empty(client):
    resp = client.get("/api/v1/courses")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 0


def test_courses_list_with_one(client, app_context):
    # seed one department and course
    dep = Department(code="CS", name="Computer Science")
    db.session.add(dep)
    db.session.commit()

    c = Course(code="CS101", title="Intro to CS", department_id=dep.id, credits=3.0, level="Undergraduate")
    db.session.add(c)
    db.session.commit()

    resp = client.get("/api/v1/courses")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["total"] == 1
    assert data["courses"][0]["code"] == "CS101"

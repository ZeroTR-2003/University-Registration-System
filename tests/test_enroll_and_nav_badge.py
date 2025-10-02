from app.models import db
from app.models.notification import Notification
from app.models.enrollment import Enrollment
from tests.helpers import create_student, seed_simple_course


def test_student_can_enroll_without_prereqs(authenticated_student_client, app_context):
    # Ensure a section exists
    section = seed_simple_course()

    # Enroll via route
    resp = authenticated_student_client.post(f"/student/enroll/{section.id}", data={"csrf_token": "whatever"}, follow_redirects=False)
    # Expect redirect after POST
    assert resp.status_code in (302, 303)

    # Enrollment exists and status is Enrolled or Waitlisted depending on capacity
    student_user = create_student("student@test.edu")
    e = db.session.query(Enrollment).filter_by(student_id=student_user.student_profile.id, course_section_id=section.id).first()
    assert e is not None


def test_nav_shows_unread_count(authenticated_student_client, app_context):
    # Create notifications for the logged-in user
    from app.models.user import User
    u = User.query.filter_by(email="student@test.edu").first()
    for _ in range(3):
        db.session.add(Notification(user_id=u.id, notification_type='system', title='N', message='Test'))
    db.session.commit()

    # Load a page that renders the global nav
    resp = authenticated_student_client.get('/student/browse')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'data-test="unread-count"' in html
    assert '>3<' in html  # unread count badge shows 3

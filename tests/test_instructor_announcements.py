from app.models import db
from app.models.announcement import Announcement
from tests.helpers import seed_simple_course


def test_instructor_announcements_filtering(authenticated_instructor_client, app_context):
    # Seed a section and assign to instructor
    from app.models.profile import InstructorProfile
    instr = InstructorProfile.query.first()
    section = seed_simple_course()
    section.instructor_id = instr.id
    db.session.commit()

    # Create announcements: one admin-only, one instructor-targeted for this section
    admin_only = Announcement(
        author_id=instr.user_id,
        title='Admin Only Maintenance',
        body='For admins only',
        announcement_type='System',
        target_roles=['Admin']
    )
    instr_ann = Announcement(
        author_id=instr.user_id,
        course_section_id=section.id,
        title='Instructor Notice',
        body='This is relevant to your course section',
        announcement_type='General',
        target_roles=['Instructor']
    )
    db.session.add(admin_only)
    db.session.add(instr_ann)
    db.session.commit()

    resp = authenticated_instructor_client.get('/instructor/announcements')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'Instructor Notice' in html
    assert 'Admin Only Maintenance' not in html

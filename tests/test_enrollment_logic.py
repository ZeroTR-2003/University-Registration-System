from app.models import db
from app.models.enrollment import Enrollment, EnrollmentStatus
from tests.helpers import create_student, seed_simple_course


def test_waitlist_promotion(client, app_context):
    # Seed course with capacity 1 and two students
    section = seed_simple_course()
    s1 = create_student("s1@example.com")
    s2 = create_student("s2@example.com")

    # Enroll first student -> ENROLLED
    e1 = Enrollment(student_id=s1.student_profile.id, course_section_id=section.id)
    e1.enroll()
    db.session.add(e1)
    db.session.commit()
    assert e1.status == EnrollmentStatus.ENROLLED
    assert section.enrolled_count == 1

    # Enroll second student -> WAITLISTED
    e2 = Enrollment(student_id=s2.student_profile.id, course_section_id=section.id)
    e2.enroll()
    db.session.add(e2)
    db.session.commit()
    assert e2.status == EnrollmentStatus.WAITLISTED
    assert section.waitlist_count == 1

    # Drop first student -> promote second
    e1.drop(reason="testing")
    db.session.commit()
    section.promote_from_waitlist()
    db.session.commit()

    db.session.refresh(e2)
    assert e2.status == EnrollmentStatus.ENROLLED

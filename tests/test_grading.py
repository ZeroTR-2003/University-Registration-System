from app.models import db
from app.models.enrollment import Enrollment, EnrollmentStatus
from tests.helpers import create_student, seed_simple_course


def test_set_grade_and_gpa(client, app_context):
    section = seed_simple_course()
    s1 = create_student("g1@example.com")

    e = Enrollment(student_id=s1.student_profile.id, course_section_id=section.id)
    e.enroll()
    db.session.add(e)
    db.session.commit()

    # Set grade
    e.set_grade('A')
    db.session.commit()

    assert e.status == EnrollmentStatus.COMPLETED
    s1.student_profile.calculate_gpa()
    assert s1.student_profile.gpa >= 3.9

from datetime import date, datetime
from app.models import db
from app.models.user import User, Role
from app.models.course import Department, Course, CourseSection
from app.models.profile import StudentProfile, InstructorProfile


def _ensure_role(user: User, role_name: str):
    role = Role.query.filter_by(name=role_name).first()
    if role and not any(r.name == role_name for r in getattr(user, 'roles', [])):
        user.roles.append(role)


def create_student(email: str, first: str = "Test", last: str = "Student") -> User:
    existing = User.query.filter_by(email=email).first()
    if existing:
        # Ensure student role and profile exist
        _ensure_role(existing, Role.STUDENT)
        if not existing.student_profile:
            sn = f"S{datetime.now().year}{existing.id:05d}"
            prof = StudentProfile(user_id=existing.id, student_number=sn, enrollment_year=datetime.now().year)
            db.session.add(prof)
        db.session.commit()
        return existing

    user = User(email=email, first_name=first, last_name=last, is_active=True)
    user.set_password("pass12345")
    _ensure_role(user, Role.STUDENT)
    db.session.add(user)
    db.session.flush()
    sn = f"S{datetime.now().year}{user.id:05d}"
    prof = StudentProfile(user_id=user.id, student_number=sn, enrollment_year=datetime.now().year)
    db.session.add(prof)
    db.session.commit()
    return user


def create_admin(email: str = "admin@test.edu", first: str = "Admin", last: str = "User") -> User:
    """Create an admin user for testing."""
    existing = User.query.filter_by(email=email).first()
    if existing:
        _ensure_role(existing, Role.ADMIN)
        db.session.commit()
        return existing

    user = User(email=email, first_name=first, last_name=last, is_active=True)
    user.set_password("adminpass123")
    _ensure_role(user, Role.ADMIN)
    db.session.add(user)
    db.session.commit()
    return user


def create_instructor(email: str = "instructor@test.edu", first: str = "John", last: str = "Instructor") -> User:
    """Create an instructor user for testing."""
    existing = User.query.filter_by(email=email).first()
    if existing:
        _ensure_role(existing, Role.INSTRUCTOR)
        if not existing.instructor_profile:
            emp_no = f"I{datetime.now().year}{existing.id:05d}"
            prof = InstructorProfile(
                user_id=existing.id,
                employee_number=emp_no,
                title="Assistant Professor",
                hire_date=date.today()
            )
            db.session.add(prof)
        db.session.commit()
        return existing

    user = User(email=email, first_name=first, last_name=last, is_active=True)
    user.set_password("instructorpass123")
    _ensure_role(user, Role.INSTRUCTOR)
    db.session.add(user)
    db.session.flush()
    prof = InstructorProfile(
        user_id=user.id,
        employee_number=f"I{datetime.now().year}{user.id:05d}",
        title="Assistant Professor",
        hire_date=date.today()
    )
    db.session.add(prof)
    db.session.commit()
    return user


def create_registrar(email: str = "registrar@test.edu", first: str = "Jane", last: str = "Registrar") -> User:
    """Create a registrar user for testing."""
    existing = User.query.filter_by(email=email).first()
    if existing:
        _ensure_role(existing, Role.REGISTRAR)
        db.session.commit()
        return existing

    user = User(email=email, first_name=first, last_name=last, is_active=True)
    user.set_password("registrarpass123")
    _ensure_role(user, Role.REGISTRAR)
    db.session.add(user)
    db.session.commit()
    return user


def login_user(client, email: str, password: str):
    """Helper to log in a user via the test client."""
    return client.post('/auth/login', data={
        'email': email,
        'password': password
    }, follow_redirects=False)


def seed_simple_course():
    dep = Department.query.filter_by(code="CS").first()
    if not dep:
        dep = Department(code="CS", name="Computer Science")
        db.session.add(dep)
        db.session.commit()
    c = Course.query.filter_by(code="CS101").first()
    if not c:
        c = Course(code="CS101", title="Intro to CS", description="Basics", department_id=dep.id, credits=3.0, level="Undergraduate")
        db.session.add(c)
        db.session.commit()
    sec = CourseSection.query.filter_by(course_id=c.id, section_code="01", term="Spring 2025").first()
    if not sec:
        sec = CourseSection(course_id=c.id, section_code="01", term="Spring 2025", capacity=1, schedule={"days":["Mon"],"start":"10:00","end":"11:00"}, start_date=date(2025,1,1), end_date=date(2025,5,1))
        db.session.add(sec)
        db.session.commit()
    return sec

"""Authentication-related services."""
from datetime import datetime
from app.models import db
from app.models.user import User, Role
from app.models.profile import StudentProfile, InstructorProfile


def register_user(email: str, password: str, first_name: str, last_name: str, role_name: str | None = None) -> User:
    email = email.strip().lower()
    if User.query.filter_by(email=email).first():
        raise ValueError("Email already registered")

    user = User(
        email=email,
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        is_active=True,
        email_verified=False,
    )
    user.set_password(password)

    if role_name is None:
        role_name = Role.STUDENT
    role = Role.query.filter_by(name=role_name).first()
    if role:
        user.roles.append(role)

    db.session.add(user)
    db.session.flush()

    # Create profile automatically based on role
    if role_name == Role.STUDENT:
        # Generate per-year student number (YYYY<N>); do not overwrite existing formats
        try:
            from app.services.identifiers import generate_student_number
            student_number = generate_student_number()
        except Exception:
            # Fallback to legacy format if generator fails
            student_number = f"S{datetime.now().year}{user.id:05d}"
        prof = StudentProfile(user_id=user.id, student_number=student_number, enrollment_year=datetime.now().year, academic_status='Active')
        db.session.add(prof)
    elif role_name == Role.INSTRUCTOR:
        count = InstructorProfile.query.count() + 1
        employee_number = f"E{datetime.now().year}{count:05d}"
        prof = InstructorProfile(user_id=user.id, employee_number=employee_number, hire_date=datetime.now().date())
        db.session.add(prof)

    db.session.commit()
    return user


def authenticate(email: str, password: str) -> User | None:
    email = (email or '').strip().lower()
    user = User.query.filter_by(email=email).first()
    # If user exists, enforce lockout before password check
    if user and user.is_locked():
        return None
    if not user or not user.check_password(password):
        # Record failed attempt if we have a user
        if user:
            user.record_failed_login()
            db.session.commit()
        return None
    if not user.is_active:
        return None
    user.record_login()
    db.session.commit()
    return user

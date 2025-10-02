"""Seed database with sample data for development."""

from datetime import date
from app import create_app, db
from app.models import (
    Role, User, Department, Course, CourseSection,
    InstructorProfile
)


def seed_database(config_name: str = 'development'):
    app = create_app(config_name)
    with app.app_context():
        # Ensure roles exist
        Role.insert_default_roles()

        # Create a sample instructor
        instructor_user = User.query.filter_by(email='instructor@university.edu').first()
        if not instructor_user:
            instructor_user = User(
                email='instructor@university.edu',
                first_name='Jane',
                last_name='Doe',
                is_active=True,
                email_verified=True,
            )
            instructor_user.set_password('password123')
            instructor_role = Role.query.filter_by(name=Role.INSTRUCTOR).first()
            if instructor_role:
                instructor_user.roles.append(instructor_role)
            db.session.add(instructor_user)
            db.session.commit()

        if not instructor_user.instructor_profile:
            profile = InstructorProfile(
                user_id=instructor_user.id,
                employee_number='E202500001',
                hire_date=date.today(),
            )
            db.session.add(profile)
            db.session.commit()

        # Create a department
        cs = Department.query.filter_by(code='CS').first()
        if not cs:
            cs = Department(code='CS', name='Computer Science')
            db.session.add(cs)
            db.session.commit()

        # Create a course
        cs101 = Course.query.filter_by(code='CS101').first()
        if not cs101:
            cs101 = Course(
                code='CS101', title='Intro to Computer Science',
                description='Basics of CS', department_id=cs.id, credits=3.0,
                level='Undergraduate'
            )
            db.session.add(cs101)
            db.session.commit()

        # Create a section
        from datetime import timedelta
        section = CourseSection.query.filter_by(course_id=cs101.id, section_code='01', term='Spring 2025').first()
        if not section:
            section = CourseSection(
                course_id=cs101.id,
                section_code='01',
                term='Spring 2025',
                instructor_id=instructor_user.instructor_profile.id if instructor_user.instructor_profile else None,
                capacity=30,
                schedule={"days": ["Mon", "Wed"], "start": "10:00", "end": "11:15"},
                start_date=date(2025, 1, 15),
                end_date=date(2025, 5, 1),
                delivery_mode='In-Person',
                status='Open'
            )
            db.session.add(section)
            db.session.commit()

        print('Seed data inserted successfully.')

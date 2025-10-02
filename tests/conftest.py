import os
import pytest
from app import create_app
from app.models import db
from app.models.user import Role
from tests.helpers import create_admin, create_instructor, create_student, create_registrar, login_user


@pytest.fixture(scope="function")
def app():
    # Ensure testing config
    os.environ["FLASK_CONFIG"] = "testing"
    application = create_app("testing")

    with application.app_context():
        db.create_all()
        # default roles
        Role.insert_default_roles()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def app_context(app, request):
    with app.app_context():
        # Seed minimal data for enrollment_engine tests only
        if 'test_enrollment_engine.py' in str(request.node.fspath):
            try:
                from tests.helpers import seed_simple_course
                seed_simple_course()
            except Exception:
                pass
        yield


@pytest.fixture()
def admin_user(app_context):
    """Create and return an admin user."""
    return create_admin()


@pytest.fixture()
def instructor_user(app_context):
    """Create and return an instructor user."""
    return create_instructor()


@pytest.fixture()
def student_user(app_context):
    """Create and return a student user."""
    return create_student(email="student@test.edu", first="Test", last="Student")


@pytest.fixture()
def registrar_user(app_context):
    """Create and return a registrar user."""
    return create_registrar()


@pytest.fixture()
def authenticated_admin_client(client, admin_user):
    """Return a test client with an authenticated admin user."""
    login_user(client, admin_user.email, "adminpass123")
    return client


@pytest.fixture()
def authenticated_instructor_client(client, instructor_user):
    """Return a test client with an authenticated instructor user."""
    login_user(client, instructor_user.email, "instructorpass123")
    return client


@pytest.fixture()
def authenticated_student_client(client, student_user):
    """Return a test client with an authenticated student user."""
    login_user(client, student_user.email, "pass12345")
    return client

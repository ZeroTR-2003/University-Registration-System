import pytest
from app.models.course import Department, Course, CourseSection
from app.models import db
from datetime import date


def test_admin_pages_require_login():
    """Test that admin pages redirect unauthenticated users."""
    try:
        from app import create_app
    except Exception as e:
        pytest.skip(f"create_app not available: {e}")

    app = create_app()  # use default config
    app.config.update(
        TESTING=True,
    )

    client = app.test_client()

    # Pages to smoke-test for existence and login requirement
    urls = [
        "/admin/courses",
        "/admin/departments",
        "/admin/sections",
        "/admin/users",
    ]

    for url in urls:
        resp = client.get(url, follow_redirects=False)
        # Should redirect to login because not authenticated
        assert resp.status_code in (302, 401, 403), f"Unexpected status for {url}: {resp.status_code}"


def test_admin_dashboard_access(authenticated_admin_client):
    """Test admin can access admin dashboard."""
    resp = authenticated_admin_client.get('/admin/dashboard', follow_redirects=True)
    assert resp.status_code == 200


def test_admin_courses_list(authenticated_admin_client, app_context):
    """Test admin can view courses list."""
    # Create test department and course
    dept = Department(code="CS", name="Computer Science")
    db.session.add(dept)
    db.session.commit()
    
    course = Course(
        code="CS101",
        title="Intro to Computer Science",
        description="Introduction to programming",
        department_id=dept.id,
        credits=3.0,
        level="Undergraduate"
    )
    db.session.add(course)
    db.session.commit()
    
    resp = authenticated_admin_client.get('/admin/courses')
    assert resp.status_code == 200
    assert b'CS101' in resp.data or b'Intro to Computer Science' in resp.data


def test_admin_courses_pagination(authenticated_admin_client, app_context):
    """Test courses pagination with per_page parameter."""
    # Create test department
    dept = Department(code="MATH", name="Mathematics")
    db.session.add(dept)
    db.session.commit()
    
    # Create multiple courses
    for i in range(15):
        course = Course(
            code=f"MATH{100+i}",
            title=f"Math Course {i}",
            description=f"Description {i}",
            department_id=dept.id,
            credits=3.0,
            level="Undergraduate"
        )
        db.session.add(course)
    db.session.commit()
    
    # Test with per_page=12
    resp = authenticated_admin_client.get('/admin/courses?per_page=12')
    assert resp.status_code == 200
    
    # Test pagination navigation
    resp = authenticated_admin_client.get('/admin/courses?page=2&per_page=12')
    assert resp.status_code == 200


def test_admin_departments_list(authenticated_admin_client, app_context):
    """Test admin can view departments list."""
    dept = Department(code="ENG", name="Engineering")
    db.session.add(dept)
    db.session.commit()
    
    resp = authenticated_admin_client.get('/admin/departments')
    assert resp.status_code == 200
    assert b'ENG' in resp.data or b'Engineering' in resp.data


def test_admin_sections_list(authenticated_admin_client, app_context):
    """Test admin can view sections list."""
    # Create test data
    dept = Department(code="PHYS", name="Physics")
    db.session.add(dept)
    db.session.commit()
    
    course = Course(
        code="PHYS101",
        title="Physics I",
        description="Intro to Physics",
        department_id=dept.id,
        credits=4.0,
        level="Undergraduate"
    )
    db.session.add(course)
    db.session.commit()
    
    section = CourseSection(
        course_id=course.id,
        section_code="01",
        term="Spring 2025",
        capacity=30,
        start_date=date(2025, 1, 15),
        end_date=date(2025, 5, 15)
    )
    db.session.add(section)
    db.session.commit()
    
    resp = authenticated_admin_client.get('/admin/sections')
    assert resp.status_code == 200


def test_admin_sections_filter_by_term(authenticated_admin_client, app_context):
    """Test sections filter by term."""
    dept = Department(code="CHEM", name="Chemistry")
    db.session.add(dept)
    db.session.commit()
    
    course = Course(
        code="CHEM101",
        title="Chemistry I",
        description="Intro to Chemistry",
        department_id=dept.id,
        credits=4.0,
        level="Undergraduate"
    )
    db.session.add(course)
    db.session.commit()
    
    # Create sections for different terms
    section1 = CourseSection(
        course_id=course.id,
        section_code="01",
        term="Spring 2025",
        capacity=25,
        start_date=date(2025, 1, 15),
        end_date=date(2025, 5, 15)
    )
    section2 = CourseSection(
        course_id=course.id,
        section_code="02",
        term="Fall 2024",
        capacity=25,
        start_date=date(2024, 8, 15),
        end_date=date(2024, 12, 15)
    )
    db.session.add_all([section1, section2])
    db.session.commit()
    
    # Filter by Spring 2025
    resp = authenticated_admin_client.get('/admin/sections?term=Spring+2025')
    assert resp.status_code == 200


def test_admin_users_list(authenticated_admin_client):
    """Test admin can view users list."""
    resp = authenticated_admin_client.get('/admin/users')
    assert resp.status_code == 200


def test_student_cannot_access_admin(authenticated_student_client):
    """Test that students cannot access admin pages."""
    resp = authenticated_student_client.get('/admin/courses', follow_redirects=False)
    # Should either redirect or return 403 Forbidden
    assert resp.status_code in (302, 403)


def test_instructor_cannot_access_admin(authenticated_instructor_client):
    """Test that instructors cannot access admin-only pages."""
    resp = authenticated_instructor_client.get('/admin/users', follow_redirects=False)
    # Should either redirect or return 403 Forbidden
    assert resp.status_code in (302, 403)

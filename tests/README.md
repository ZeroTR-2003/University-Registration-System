# Testing Guide

## Overview
This directory contains all tests for the University Registration System. Tests are organized by feature area and use pytest with Flask-specific fixtures.

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures (app, client, authenticated users)
├── helpers.py               # Test helper functions (create users, seed data)
├── test_admin_routes.py     # Admin interface tests
├── test_auth_api.py         # Authentication API tests
├── test_courses_api.py      # Courses API tests
├── test_enrollment_engine.py # Enrollment business logic tests
├── test_enrollment_logic.py  # Additional enrollment tests
├── test_grading.py          # Grading system tests
├── test_health.py           # Health check tests
└── README.md                # This file
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_admin_routes.py -v
pytest tests/test_enrollment_engine.py -v
```

### Run Specific Test
```bash
pytest tests/test_admin_routes.py::test_admin_courses_list -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Tests Matching Pattern
```bash
pytest -k "admin" -v           # All tests with "admin" in name
pytest -k "enrollment" -v      # All tests with "enrollment" in name
```

## Test Fixtures

### Application Fixtures
- `app` - Flask application instance with test config
- `client` - Test client for making HTTP requests
- `app_context` - Application context for database operations

### User Fixtures
- `admin_user` - Admin user instance
- `instructor_user` - Instructor user instance
- `student_user` - Student user instance
- `registrar_user` - Registrar user instance

### Authenticated Client Fixtures
- `authenticated_admin_client` - Test client logged in as admin
- `authenticated_instructor_client` - Test client logged in as instructor
- `authenticated_student_client` - Test client logged in as student

## Helper Functions

### Create Users
```python
from tests.helpers import create_admin, create_instructor, create_student

def test_example(app_context):
    admin = create_admin(email="test@example.edu")
    instructor = create_instructor(email="prof@example.edu")
    student = create_student(email="student@example.edu")
```

### Login User
```python
from tests.helpers import login_user

def test_example(client, admin_user):
    login_user(client, admin_user.email, "adminpass123")
    # Now client is authenticated
```

### Seed Data
```python
from tests.helpers import seed_simple_course

def test_example(app_context):
    section = seed_simple_course()  # Creates CS dept, CS101 course, and a section
```

## Writing New Tests

### Basic Test Structure
```python
def test_something(app_context):
    """Test description."""
    # Arrange - set up test data
    # Act - perform the action
    # Assert - verify results
    assert result == expected
```

### Test with Authenticated User
```python
def test_admin_action(authenticated_admin_client, app_context):
    """Test admin can perform action."""
    resp = authenticated_admin_client.get('/admin/dashboard')
    assert resp.status_code == 200
```

### Test with Database
```python
from app.models import db
from app.models.course import Department

def test_create_department(app_context):
    """Test department creation."""
    dept = Department(code="TEST", name="Test Department")
    db.session.add(dept)
    db.session.commit()
    
    assert dept.id is not None
    assert dept.code == "TEST"
```

## Test Configuration

Tests use the `TestingConfig` from `config.py`:
- In-memory SQLite database
- CSRF disabled
- Fast password hashing (bcrypt rounds = 4)
- Memory-based rate limiting
- JWT tokens expire in 5 minutes

## Common Patterns

### Test Authorization
```python
def test_student_cannot_access_admin(authenticated_student_client):
    """Students should not access admin pages."""
    resp = authenticated_student_client.get('/admin/courses', follow_redirects=False)
    assert resp.status_code in (302, 403)
```

### Test Pagination
```python
def test_courses_pagination(authenticated_admin_client, app_context):
    """Test pagination works correctly."""
    # Create 15 courses
    for i in range(15):
        create_course(code=f"COURSE{i}")
    
    resp = authenticated_admin_client.get('/admin/courses?per_page=10')
    assert resp.status_code == 200
```

### Test Filters
```python
def test_sections_filter_by_term(authenticated_admin_client, app_context):
    """Test filtering sections by term."""
    # Create sections for different terms
    create_section(term="Spring 2025")
    create_section(term="Fall 2024")
    
    resp = authenticated_admin_client.get('/admin/sections?term=Spring+2025')
    assert resp.status_code == 200
    assert b'Spring 2025' in resp.data
```

## Debugging Tests

### Show Print Statements
```bash
pytest tests/ -v -s
```

### Stop on First Failure
```bash
pytest tests/ -v -x
```

### Show Local Variables on Failure
```bash
pytest tests/ -v -l
```

### Run with PDB Debugger
```bash
pytest tests/ -v --pdb
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:
- No external dependencies (Redis, PostgreSQL) required for basic tests
- In-memory database for speed
- Deterministic results
- Fast execution (< 5 seconds for basic tests)

## Best Practices

1. **Test Isolation:** Each test should be independent and not rely on other tests
2. **Use Fixtures:** Leverage pytest fixtures for common setup
3. **Clear Names:** Test names should describe what is being tested
4. **Arrange-Act-Assert:** Follow the AAA pattern for clarity
5. **Test Edge Cases:** Don't just test happy paths
6. **Mock External Services:** Use mocks for email, APIs, etc.
7. **Keep Tests Fast:** Avoid unnecessary database operations

## Troubleshooting

### Database Errors
If you see database errors, ensure:
- `SQLALCHEMY_ENGINE_OPTIONS = {}` in TestingConfig (SQLite doesn't support pool_size)
- Database is properly initialized in conftest.py
- Migrations are up to date

### Import Errors
If you see import errors:
- Ensure you're in the project root directory
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify Python path includes project directory

### Authentication Errors
If authentication tests fail:
- Check that roles are created: `Role.insert_default_roles()`
- Verify password in login_user matches create_user password
- Ensure session handling is correct in test client

## Coverage Goals

Target test coverage by component:
- Models: 90%+
- Routes/Views: 80%+
- Business Logic: 95%+
- API Endpoints: 90%+
- Overall: 85%+

## Next Steps

Priority areas for additional tests:
1. ✅ Admin routes (COMPLETE - 10 tests)
2. ✅ Enrollment engine (COMPLETE - 10 tests)
3. [ ] POST operations (create/edit/delete with CSRF)
4. [ ] Bulk actions
5. [ ] Student enrollment flows
6. [ ] Instructor features
7. [ ] Error handling and edge cases
8. [ ] API endpoints

---

For questions or issues with tests, consult the main project documentation or open an issue.

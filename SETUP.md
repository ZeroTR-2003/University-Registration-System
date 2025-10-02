# Setup and Run Instructions

## Prerequisites
- Python 3.11+ (3.13 works)
- Git (optional, for version control)

## Quick Start (Windows PowerShell)

### 1. Navigate to project directory
```powershell
cd C:\DevProjects\university-registration-system\university-registration-system
```

### 2. Create and activate virtual environment
If `.venv` doesn't exist or is broken:
```powershell
python -m venv .venv
```

Activate:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```powershell
pip install -r requirements.txt
```

### 4. Initialize database and seed sample data
```powershell
python .\init_db.py
```

This creates:
- SQLite database at `dev_university.db`
- Default roles (Admin, Student, Instructor, Registrar)
- Admin user: `admin@university.edu` / `admin123`

### 5. (Optional) Seed additional sample data
```powershell
& .\.venv\Scripts\flask.exe seed-db
```

This adds:
- Sample instructor
- Computer Science department
- CS101 course
- Open section for Spring 2025

### 6. Run the application
```powershell
python .\run.py
```

The app will start at:
- Main app: http://localhost:5000
- API docs (Swagger): http://localhost:5000/api/docs

### 7. Run tests
```powershell
pytest -q
```

## Default Credentials

After running `init_db.py`:
- **Admin**: `admin@university.edu` / `admin123`

After running `flask seed-db`:
- **Instructor**: `instructor@university.edu` / `password123`

## Common Commands

### Create additional admin user
```powershell
& .\.venv\Scripts\flask.exe create-admin
```

### Database migrations (if you modify models)
```powershell
& .\.venv\Scripts\flask.exe db migrate -m "Description"
& .\.venv\Scripts\flask.exe db upgrade
```

### Run with specific config
```powershell
$env:FLASK_CONFIG="development"
python .\run.py
```

### Run linting
```powershell
flake8
```

### Run formatting check
```powershell
black --check .
```

### Apply formatting
```powershell
black .
```

## Project Structure
```
university-registration-system/
├── app/
│   ├── api/              # REST API endpoints
│   ├── models/           # Database models
│   ├── services/         # Business logic layer
│   ├── templates/        # Jinja2 HTML templates
│   ├── auth/             # Authentication blueprint
│   ├── student/          # Student portal
│   ├── instructor/       # Instructor portal
│   └── admin/            # Admin portal
├── tests/                # Test suite
├── migrations/           # Alembic migrations
├── .env                  # Environment variables
├── config.py             # Configuration classes
├── requirements.txt      # Python dependencies
└── run.py                # Application entry point
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (returns JWT tokens)
- `POST /api/v1/auth/refresh` - Refresh access token
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/logout` - Logout

### Courses
- `GET /api/v1/courses` - List courses (cached 60s)
- `GET /api/v1/courses/<id>` - Get course details
- `POST /api/v1/courses` - Create course (admin/instructor)
- `PUT /api/v1/courses/<id>` - Update course
- `DELETE /api/v1/courses/<id>` - Delete course

### Enrollments
- `GET /api/v1/enrollments` - Student's enrollments
- `GET /api/v1/enrollments/check` - Check eligibility
- `POST /api/v1/enrollments` - Enroll in course
- `DELETE /api/v1/enrollments/<id>` - Drop course

### Users
- `GET /api/v1/users/me` - Current user profile
- `GET /api/v1/users` - List users (admin only)
- `GET /api/v1/users/<id>` - Get user (self or admin)

## Testing the API

### Register a student
```powershell
$body = @{
    email = "student@example.com"
    password = "pass12345"
    first_name = "John"
    last_name = "Doe"
    role = "Student"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:5000/api/v1/auth/register -Method POST -Body $body -ContentType "application/json"
```

### Login
```powershell
$body = @{
    email = "student@example.com"
    password = "pass12345"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri http://localhost:5000/api/v1/auth/login -Method POST -Body $body -ContentType "application/json"
$token = $response.access_token
```

### List courses
```powershell
$headers = @{Authorization = "Bearer $token"}
Invoke-RestMethod -Uri http://localhost:5000/api/v1/courses -Headers $headers
```

## Troubleshooting

### Import errors
```powershell
# Ensure venv is activated
.\.venv\Scripts\Activate.ps1
# Reinstall dependencies
pip install -r requirements.txt
```

### Database errors
```powershell
# Delete and recreate database
Remove-Item dev_university.db -ErrorAction SilentlyContinue
python .\init_db.py
```

### Port already in use
```powershell
# Change port in run.py or set environment variable
$env:PORT="8000"
python .\run.py
```

## Docker (Optional)

For production deployment with PostgreSQL and Redis:

```powershell
docker-compose up --build
```

This starts:
- PostgreSQL database
- Redis cache
- Flask web app
- Celery worker
- Celery beat scheduler

## Next Steps

1. Explore the API at http://localhost:5000/api/docs
2. Login as admin to manage users and courses
3. Register students and instructors
4. Create courses and sections
5. Test enrollment workflows
6. Review audit logs and analytics

For more details, see README.md.
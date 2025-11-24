# University Course Registration System

A production-ready web application for university course management and student registration built with Flask and SQLAlchemy.

## Features

### Core Functionality
- **User Authentication & Authorization**: Role-based access control (RBAC) with Admin, Instructor, Student, and Registrar roles
- **Course Management**: Full CRUD operations for courses, departments, and course sections
- **Smart Enrollment System**: 
  - Automatic conflict detection for scheduling
  - Prerequisites checking
  - Seat limit enforcement
  - Waitlist management with automatic promotion
- **Grade Management**: Assignment creation, submission tracking, and grade calculation
- **Analytics Dashboard**: Real-time statistics on enrollments, grades, and course completion rates
- **Notification System**: Email and in-app notifications for important events

### Advanced Features
- **Mobile-Responsive Design**: Works seamlessly on desktop and mobile devices
- **Progressive Web App (PWA)**: Installable app with offline capabilities
- **File Upload System**: Support for assignment submissions and course materials
- **Audit Logging**: Complete tracking of all system activities
- **Search & Filter**: Advanced search capabilities across all entities
- **Rich Content Support**: Multimedia content in courses and announcements

## Technology Stack

- **Backend**: Flask, SQLAlchemy, Flask-Login, Flask-JWT-Extended
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Jinja2 templates, Bootstrap/Tailwind CSS, HTMX for interactivity
- **Caching**: Redis
- **Task Queue**: Celery
- **Authentication**: JWT tokens and session-based auth
- **Testing**: pytest, pytest-flask
- **Deployment**: Docker, docker-compose, GitHub Actions CI/CD

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (for production)
- Redis 6+ (for caching and Celery)
- Node.js 18+ (for frontend build tools, optional)

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/university-registration-system.git
cd university-registration-system
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Unix/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Initialize Database
```bash
# Create database tables
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Insert default roles
flask init-db

# Create admin user
flask create-admin

# (Optional) Seed with sample data
flask seed-db
```

### 6. Run the Application
```bash
# Development mode
python run.py

# Or using Flask CLI
flask run
```

The application will be available at `http://localhost:5000`

## Docker Deployment

### Using Docker Compose
```bash
# Build and run all services
docker-compose up --build

# Run in background
docker-compose up -d

# Stop services
docker-compose down
```

### Production Deployment
```bash
# Build production image
docker build -t university-registration-system:latest .

# Run with environment variables
docker run -d \
  -p 80:5000 \
  --env-file .env.production \
  university-registration-system:latest
```

## Project Structure

```
university-registration-system/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models/               # SQLAlchemy models
│   │   ├── user.py          # User and Role models
│   │   ├── course.py        # Course-related models
│   │   ├── enrollment.py    # Enrollment with conflict detection
│   │   └── ...
│   ├── api/                 # RESTful API endpoints
│   ├── auth/                # Authentication blueprint
│   ├── services/            # Business logic layer
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS, images
├── migrations/              # Database migrations
├── tests/                   # Test suite
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker orchestration
├── Dockerfile             # Container definition
└── run.py                 # Application entry point
```

## Database Schema

The database follows strict normalization principles:

- **Users**: Stores user authentication and basic information
- **Roles**: RBAC roles with permissions
- **Student/Instructor Profiles**: Extended profiles for different user types
- **Courses**: Course catalog with prerequisites
- **Course Sections**: Actual course offerings per term
- **Enrollments**: Many-to-many relationship with conflict detection
- **Assignments & Submissions**: Assignment tracking and grading
- **Rooms & Buildings**: Physical location management

Key design principles:
- No derived data storage (e.g., age calculated from birth_date)
- Atomic fields (first_name and last_name stored separately)
- Proper foreign key constraints
- Composite primary keys for association tables

## API Documentation

### Authentication Endpoints
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh JWT token

### Course Management
- `GET /api/v1/courses` - List all courses
- `GET /api/v1/courses/<id>` - Get course details
- `POST /api/v1/courses` - Create new course (Admin/Instructor)
- `PUT /api/v1/courses/<id>` - Update course (Admin/Instructor)
- `DELETE /api/v1/courses/<id>` - Delete course (Admin)

### Enrollment
- `POST /api/v1/enrollments` - Enroll in course
- `DELETE /api/v1/enrollments/<id>` - Drop course
- `GET /api/v1/enrollments/check` - Check enrollment eligibility

### Full API documentation available at `/api/docs` when running the application.

## Testing

### Run All Tests
```bash
pytest
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Run tests with verbose output
pytest -v
```

## Security Features

- **Password Hashing**: Bcrypt with salt
- **JWT Tokens**: Secure API authentication
- **CSRF Protection**: For form submissions
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy
- **XSS Protection**: Template auto-escaping
- **Rate Limiting**: Prevents brute force attacks
- **Input Validation**: Comprehensive validation on all inputs
- **Audit Logging**: Tracks all sensitive operations

## Performance Optimizations

- **Database Indexing**: On frequently queried columns
- **Query Optimization**: Eager loading to prevent N+1 queries
- **Caching**: Redis caching for frequently accessed data
- **Pagination**: All list endpoints support pagination
- **Lazy Loading**: For large datasets
- **Connection Pooling**: Efficient database connection management

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Development Guidelines

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation as needed
- Use meaningful commit messages
- Keep database migrations atomic

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email support@university.edu or open an issue in the GitHub repository.

## Acknowledgments

- Flask and its ecosystem contributors
- SQLAlchemy for excellent ORM capabilities
- The open-source community

## Roadmap

### Version 2.0
- [ ] Real-time collaboration features
- [ ] AI-powered course recommendations
- [ ] Mobile native apps
- [ ] Video lecture integration
- [ ] Advanced analytics with ML insights
- [ ] Multi-language support
- [ ] Integration with external LMS platforms

## Environment Variables

Key environment variables (see `.env.example` for full list):

```env
# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/university_db

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-email-password

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret
```

## Monitoring & Logging

- Application logs: `logs/university.log`
- Access logs: Configure in web server
- Error tracking: Integration with Sentry (optional)
- Performance monitoring: Integration with New Relic (optional)

## Troubleshooting

### Common Issues

1. **Database connection errors**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL in .env

2. **Import errors**
   - Activate virtual environment
   - Reinstall dependencies: `pip install -r requirements.txt`

3. **Migration errors**
   - Drop and recreate database
   - Run `flask db init` again

4. **Permission errors**
   - Check file permissions
   - Ensure proper user roles are assigned

For more help, check the [documentation](docs/) or open an issue.
#   U n i v e r s i t y - R e g i s t r a t i o n - S y s t e m  
 
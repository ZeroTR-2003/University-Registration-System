# Project Structure

```
university-registration-system/
│
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── course.py
│   │   ├── enrollment.py
│   │   ├── assignment.py
│   │   └── ...
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── courses.py
│   │   ├── enrollments.py
│   │   └── ...
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── enrollment_service.py
│   │   └── ...
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/
│   │   ├── student/
│   │   ├── instructor/
│   │   └── admin/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   └── utils/
│       ├── __init__.py
│       ├── decorators.py
│       └── validators.py
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── config.py
├── run.py
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── README.md
```

import os
os.environ['FLASK_CONFIG'] = 'testing'
from app import create_app, db
from app.models.user import User, Role

app = create_app('testing')

with app.app_context():
    db.create_all()
    Role.insert_default_roles()

    # create admin
    admin = User(email='admin@test.edu', first_name='Admin', last_name='User', is_active=True)
    admin.set_password('adminpass123')
    admin_role = Role.query.filter_by(name='Admin').first()
    # Bind admin to session before manipulating dynamic relationship
    db.session.add(admin)
    db.session.flush()
    if admin_role:
        admin.add_role(admin_role)
    db.session.commit()

    client = app.test_client()
    # login
    r = client.post('/auth/login', data={'email':'admin@test.edu','password':'adminpass123'}, follow_redirects=True)
    print('login status:', r.status_code)

    # open create get
    r = client.get('/admin/users/create')
    print('GET /admin/users/create status:', r.status_code)

    # post create student
    data = {
        'email': 'stu1@test.edu',
        'first_name': 'Stu',
        'last_name': 'Dent',
        'password': 'password123',
        'password2': 'password123',
        'role': 'student',
        'department_id': 0,
        'submit': 'Register'
    }
    r = client.post('/admin/users/create', data=data, follow_redirects=False)
    print('POST create student status:', r.status_code, 'Location:', r.headers.get('Location'))

    # post create instructor
    data2 = {
        'email': 'inst1@test.edu',
        'first_name': 'Inga',
        'last_name': 'Structor',
        'password': 'password123',
        'password2': 'password123',
        'role': 'instructor',
        'department_id': 0,
        'submit': 'Register'
    }
    r2 = client.post('/admin/users/create', data=data2, follow_redirects=False)
    print('POST create instructor status:', r2.status_code, 'Location:', r2.headers.get('Location'))

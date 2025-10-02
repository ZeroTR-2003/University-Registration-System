"""Authentication routes."""

from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user
from urllib.parse import urlparse
from datetime import datetime
from app import db
from app.auth import auth_bp
from app.models import User, Role, StudentProfile, InstructorProfile
from app.forms import LoginForm, RegistrationForm, PasswordResetRequestForm, PasswordResetForm


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if user.is_locked():
            flash('Your account is temporarily locked due to too many failed login attempts.', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account is not yet approved by an administrator. Please try again later.', 'warning')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)

        # Ensure role-based profile exists and assign identifiers if missing
        try:
            from datetime import datetime, date
            if user.is_student() and not user.student_profile:
                student_number = f"S{datetime.now().year}{user.id:05d}"
                prof = StudentProfile(
                    user_id=user.id,
                    student_number=student_number,
                    enrollment_year=datetime.now().year,
                    academic_status='Active'
                )
                db.session.add(prof)
            if user.is_instructor() and not user.instructor_profile:
                employee_number = f"E{datetime.now().year}{user.id:05d}"
                prof = InstructorProfile(
                    user_id=user.id,
                    employee_number=employee_number,
                    hire_date=date.today()
                )
                db.session.add(prof)
        except Exception:
            pass

        user.record_login()
        db.session.commit()
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            # Redirect based on user role
            if user.is_admin():
                next_page = url_for('admin.dashboard')
            elif user.is_instructor():
                next_page = url_for('instructor.dashboard')
            elif user.is_student():
                next_page = url_for('student.dashboard')
            else:
                next_page = url_for('main.dashboard')
        
        flash(f'Welcome back, {user.first_name}!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    # Populate department choices for instructors
    try:
        from app.models.course import Department
        departments = Department.query.order_by(Department.name).all()
        form.department_id.choices = [(0, 'Unassigned')] + [(d.id, d.name) for d in departments]
    except Exception:
        # In testing or if DB not ready, keep empty choices (field is optional)
        form.department_id.choices = [(0, 'Unassigned')]

    if form.validate_on_submit():
        # Create user (pending approval)
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone_number=form.phone_number.data,
            birth_date=form.birth_date.data,
            address_line1=form.address_line1.data,
            address_line2=form.address_line2.data,
            city=form.city.data,
            state=form.state.data,
            postal_code=form.postal_code.data,
            country=form.country.data,
            is_active=bool(current_app.config.get('AUTO_APPROVE_REGISTRATIONS', False))
        )
        user.set_password(form.password.data)
        
        # Assign role (stored now; profile will be created upon approval/login)
        role_name = 'Student' if form.role.data == 'student' else 'Instructor'
        role = Role.query.filter_by(name=role_name).first()
        if role:
            user.roles.append(role)
        
        db.session.add(user)
        db.session.commit()

        # Notify admins of new registration
        try:
            from app.models import Notification, Announcement
            admin_role = Role.query.filter_by(name='Admin').first()
            if admin_role and getattr(admin_role, 'users', None):
                for admin_user in admin_role.users:
                    note = Notification(
                        user_id=admin_user.id,
                        notification_type='system',
                        title='New Registration',
                        message=f"{user.full_name} ({user.email}) created an account and is pending approval.",
                        action_url=url_for('admin.users', status='pending')
                    )
                    db.session.add(note)
                # Also create a system announcement targeted to Admins
                # (Actions will appear via inbox notifications.)
                ann = Announcement(
                    author_id=admin_role.users[0].id if admin_role.users else 1,
                    title='New user registration pending approval',
                    body=f"A new user {user.full_name} ({user.email}) has registered and is awaiting approval.",
                    announcement_type='System',
                    priority='Normal',
                    target_roles=['Admin']
                )
                db.session.add(ann)
                db.session.commit()
        except Exception:
            pass
        
        flash('Registration submitted. Your account requires admin approval before you can sign in.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register', form=form)


@auth_bp.route('/logout')
def logout():
    """Handle user logout."""
    if current_user.is_authenticated:
        current_user.last_activity = datetime.utcnow()
        db.session.commit()
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Handle password reset request."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # In a real application, you would send an email here
            # For now, we'll just flash a message
            flash('Check your email for instructions to reset your password.', 'info')
        else:
            flash('No account found with that email address.', 'warning')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html', 
                         title='Reset Password', form=form)


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # In a real application, you would verify the token here
    # For now, we'll just show the form
    form = PasswordResetForm()
    if form.validate_on_submit():
        # In a real application, you would:
        # 1. Verify the token
        # 2. Get the user from the token
        # 3. Set the new password
        flash('Your password has been reset.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)

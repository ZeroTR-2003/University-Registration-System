"""Admin blueprint routes."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.admin import admin_bp
from app.forms import ProfileForm, CourseForm, CourseSectionForm, RegistrationForm, DepartmentForm, ConfirmDeleteForm, AdminUserEditForm
from app.models import User, Course, CourseSection, Department, Enrollment, Room, InstructorProfile, StudentProfile
from app.models.user import Role


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('You must be an administrator to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required
def admin_root():
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard."""
    stats = {
        'total_users': User.query.count(),
        'total_students': User.query.join(User.roles).filter_by(name='Student').count(),
        'total_instructors': User.query.join(User.roles).filter_by(name='Instructor').count(),
        'total_courses': Course.query.count(),
        'active_sections': CourseSection.query.filter_by(status='Open').count(),
        'total_enrollments': Enrollment.query.count()
    }
    
    return render_template('admin/dashboard.html',
                         title='Admin Dashboard',
                         stats=stats)


@admin_bp.route('/announcements')
@admin_required
def announcements():
    """View all announcements with basic filters."""
    from app.models import Announcement
    role = request.args.get('role')  # Admin, Instructor, Student, All
    course_id = request.args.get('course_id', type=int)
    dept_id = request.args.get('department_id', type=int)

    query = Announcement.query
    if role:
        role_norm = role.lower()
        anns = query.order_by(Announcement.published_at.desc()).all()
        filtered = []
        for a in anns:
            roles = (a.target_roles or ['All'])
            roles_norm = [r.lower() for r in roles]
            if role_norm == 'all' and ('all' in roles_norm):
                filtered.append(a)
            elif role_norm in roles_norm:
                filtered.append(a)
        anns = filtered
    else:
        anns = query.order_by(Announcement.published_at.desc()).all()

    # Optional filter by course/department
    if course_id or dept_id:
        anns2 = []
        for a in anns:
            if not a.course_section:
                anns2.append(a)
            else:
                if course_id and a.course_section.course_id == course_id:
                    anns2.append(a)
                elif dept_id and a.course_section.course.department_id == dept_id:
                    anns2.append(a)
        anns = anns2

    return render_template('admin/announcements.html', title='Announcements', announcements=anns)


@admin_bp.route('/inbox')
@admin_required
def inbox_redirect():
    return redirect(url_for('main.notifications_center'))


@admin_bp.route('/users')
@admin_required
def users():
    """Manage users with pagination and filters."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')  # 'pending', 'active', or None for all
    q = (request.args.get('q') or '').strip()

    query = User.query
    if status == 'pending':
        query = query.filter_by(is_active=False)
    elif status == 'active':
        query = query.filter_by(is_active=True)

    if q:
        like = f"%{q}%"
        query = query.filter((User.email.ilike(like)) | (User.first_name.ilike(like)) | (User.last_name.ilike(like)))

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    delete_form = ConfirmDeleteForm()
    return render_template('admin/users.html',
                         title='Manage Users',
                         users=users,
                         pagination=pagination,
                         status=status,
                         q=q,
                         delete_form=delete_form)


@admin_bp.route('/courses')
@admin_required
def courses():
    """Manage courses with filters and pagination."""
    selected_department_id = request.args.get('department_id', type=int)
    instructor_id = request.args.get('instructor_id', type=int)
    level = request.args.get('level')
    q = (request.args.get('q') or '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 18, type=int)

    query = Course.query
    if selected_department_id:
        query = query.filter_by(department_id=selected_department_id)
    if level:
        query = query.filter_by(level=level)
    if q:
        like = f"%{q}%"
        query = query.filter((Course.code.ilike(like)) | (Course.title.ilike(like)) | (Course.description.ilike(like)))
    if instructor_id:
        from app.models.course import CourseSection
        query = query.join(CourseSection, CourseSection.course_id == Course.id).filter(CourseSection.instructor_id == instructor_id).distinct()

    pagination = query.order_by(Course.code).paginate(page=page, per_page=per_page, error_out=False)
    courses = pagination.items
    departments = Department.query.order_by(Department.name).all()
    instructors = InstructorProfile.query.order_by(InstructorProfile.id).all()
    delete_form = ConfirmDeleteForm()
    return render_template('admin/courses.html',
                         title='Manage Courses',
                         courses=courses,
                         departments=departments,
                         instructors=instructors,
                         selected_department_id=selected_department_id,
                         selected_instructor_id=instructor_id,
                         level=level,
                         q=q,
                         pagination=pagination,
                         delete_form=delete_form)


@admin_bp.route('/departments')
@admin_required
def departments():
    """Manage departments with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    pagination = Department.query.order_by(Department.name).paginate(page=page, per_page=per_page, error_out=False)
    departments = pagination.items
    delete_form = ConfirmDeleteForm()
    return render_template('admin/departments.html',
                         title='Manage Departments',
                         departments=departments,
                         pagination=pagination,
                         delete_form=delete_form)


@admin_bp.route('/profile', methods=['GET', 'POST'])
@admin_required
def profile():
    """Admin profile page to update basic account info."""
    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        form.populate_obj(current_user)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('admin.profile'))

    return render_template('admin/profile.html',
                         title='My Profile',
                         form=form)


# -------- Courses CRUD --------
@admin_bp.route('/courses/create', methods=['GET', 'POST'])
@admin_required
def create_course():
    form = CourseForm()
    # Populate choices
    form.department_id.choices = [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]
    form.prerequisites.choices = [(c.id, f"{c.code} - {c.title}") for c in Course.query.order_by(Course.code).all()]

    if form.validate_on_submit():
        course = Course(
            code=form.code.data,
            title=form.title.data,
            description=form.description.data,
            department_id=form.department_id.data,
            credits=form.credits.data,
            level=form.level.data,
            max_capacity_default=form.max_capacity_default.data,
            lab_required=form.lab_required.data,
            is_active=True,
        )
        db.session.add(course)
        db.session.flush()  # get course.id
        # Set prerequisites
        if form.prerequisites.data:
            prereq_objs = Course.query.filter(Course.id.in_(form.prerequisites.data)).all()
            course.prerequisites = prereq_objs
        db.session.commit()
        flash('Course created successfully', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', title='Create Course', form=form)


@admin_bp.route('/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    form = CourseForm(obj=course)
    # Populate choices
    form.department_id.choices = [(d.id, d.name) for d in Department.query.order_by(Department.name).all()]
    form.prerequisites.choices = [(c.id, f"{c.code} - {c.title}") for c in Course.query.filter(Course.id != course.id).order_by(Course.code).all()]
    # Preselect prerequisites
    if request.method == 'GET':
        form.prerequisites.data = [p.id for p in course.prerequisites]

    if form.validate_on_submit():
        course.code = form.code.data
        course.title = form.title.data
        course.description = form.description.data
        course.department_id = form.department_id.data
        course.credits = form.credits.data
        course.level = form.level.data
        course.max_capacity_default = form.max_capacity_default.data
        course.lab_required = form.lab_required.data
        # Update prerequisites
        course.prerequisites = Course.query.filter(Course.id.in_(form.prerequisites.data or [])).all()
        db.session.commit()
        flash('Course updated successfully', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/course_form.html', title='Edit Course', form=form, course=course)


@admin_bp.route('/courses/<int:course_id>/delete', methods=['POST'])
@admin_required
def delete_course(course_id):
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        course = Course.query.get_or_404(course_id)
        # Soft delete
        course.is_active = False
        db.session.commit()
        flash('Course deactivated', 'info')
    else:
        flash('Invalid deletion request', 'danger')
    return redirect(url_for('admin.courses'))


# -------- Course Detail (Admin) --------
@admin_bp.route('/courses/<int:course_id>')
@admin_required
def course_detail_admin(course_id):
    course = Course.query.get_or_404(course_id)
    sections = CourseSection.query.filter_by(course_id=course_id).order_by(CourseSection.term.desc(), CourseSection.section_code).all()
    delete_form = ConfirmDeleteForm()
    return render_template('admin/course_detail.html', title=f"{course.code} - {course.title}", course=course, sections=sections, delete_form=delete_form)


# -------- Sections CRUD --------
@admin_bp.route('/sections/create', methods=['GET', 'POST'])
@admin_required
def create_section():
    form = CourseSectionForm()
    # Populate choices
    form.course_id.choices = [(c.id, f"{c.code} - {c.title}") for c in Course.query.order_by(Course.code).all()]
    instructor_choices = [(0, 'Unassigned')] + [
        (i.id, i.user.full_name) for i in InstructorProfile.query.order_by(InstructorProfile.id).all()
    ]
    form.instructor_id.choices = instructor_choices
    room_choices = [(0, 'Unassigned')] + [
        (r.id, f"{r.building.name if r.building else ''} {r.room_number}") for r in Room.query.order_by(Room.id).all()
    ]
    form.room_id.choices = room_choices

    # Distinct terms for autocomplete
    term_rows = CourseSection.query.with_entities(CourseSection.term).distinct().order_by(CourseSection.term.desc()).all()
    term_options = [t[0] for t in term_rows if t and t[0]]

    # Preselect course if provided via query string
    if request.method == 'GET':
        preselect_course_id = request.args.get('course_id', type=int) or request.args.get('course', type=int)
        if preselect_course_id and any(cid == preselect_course_id for cid, _ in form.course_id.choices):
            form.course_id.data = preselect_course_id

    if form.validate_on_submit():
        # Optional next redirect
        next_url = request.form.get('next')
        instructor_id = form.instructor_id.data or None
        if instructor_id == 0:
            instructor_id = None
        room_id = form.room_id.data or None
        if room_id == 0:
            room_id = None
        section = CourseSection(
            course_id=form.course_id.data,
            section_code=form.section_code.data,
            term=form.term.data,
            instructor_id=instructor_id,
            capacity=form.capacity.data,
            room_id=room_id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            delivery_mode=form.delivery_mode.data,
            allow_audit=form.allow_audit.data,
            require_permission=form.require_permission.data,
            status='Open'
        )
        db.session.add(section)
        db.session.commit()
        flash('Section created successfully', 'success')
        # Redirect to provided next URL if safe, else course detail
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('admin.course_detail_admin', course_id=section.course_id))

    # Default next target from referrer (for Cancel/back)
    next_url = request.args.get('next') or request.referrer
    return render_template('admin/section_form.html', title='Create Section', form=form, term_options=term_options, next=next_url)


@admin_bp.route('/sections/<int:section_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_section(section_id):
    section = CourseSection.query.get_or_404(section_id)
    form = CourseSectionForm(obj=section)
    form.course_id.choices = [(c.id, f"{c.code} - {c.title}") for c in Course.query.order_by(Course.code).all()]
    # Distinct terms for autocomplete
    term_rows = CourseSection.query.with_entities(CourseSection.term).distinct().order_by(CourseSection.term.desc()).all()
    term_options = [t[0] for t in term_rows if t and t[0]]
    instructor_choices = [(0, 'Unassigned')] + [
        (i.id, i.user.full_name) for i in InstructorProfile.query.order_by(InstructorProfile.id).all()
    ]
    form.instructor_id.choices = instructor_choices
    room_choices = [(0, 'Unassigned')] + [
        (r.id, f"{r.building.name if r.building else ''} {r.room_number}") for r in Room.query.order_by(Room.id).all()
    ]
    form.room_id.choices = room_choices

    if form.validate_on_submit():
        next_url = request.form.get('next')
        section.course_id = form.course_id.data
        section.section_code = form.section_code.data
        section.term = form.term.data
        section.instructor_id = None if form.instructor_id.data == 0 else form.instructor_id.data
        section.capacity = form.capacity.data
        section.room_id = None if form.room_id.data == 0 else form.room_id.data
        section.start_date = form.start_date.data
        section.end_date = form.end_date.data
        section.delivery_mode = form.delivery_mode.data
        section.allow_audit = form.allow_audit.data
        section.require_permission = form.require_permission.data
        db.session.commit()
        flash('Section updated successfully', 'success')
        # Redirect to provided next URL if safe, else course detail
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(url_for('admin.course_detail_admin', course_id=section.course_id))

    next_url = request.args.get('next') or request.referrer
    return render_template('admin/section_form.html', title='Edit Section', form=form, term_options=term_options, next=next_url)


@admin_bp.route('/sections/<int:section_id>/delete', methods=['POST'])
@admin_required
def delete_section(section_id):
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        section = CourseSection.query.get_or_404(section_id)
        db.session.delete(section)
        db.session.commit()
        flash('Section deleted', 'info')
    else:
        flash('Invalid deletion request', 'danger')
    # Redirect back to referring page to preserve context/filters
    return redirect(request.referrer or url_for('admin.sections'))


# -------- Departments CRUD --------
@admin_bp.route('/departments/create', methods=['GET', 'POST'])
@admin_required
def create_department():
    form = DepartmentForm()
    if form.validate_on_submit():
        dept = Department(
            code=form.code.data,
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(dept)
        db.session.commit()
        flash('Department created successfully', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', title='Create Department', form=form)


@admin_bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    form = DepartmentForm(obj=dept)
    if form.validate_on_submit():
        dept.code = form.code.data
        dept.name = form.name.data
        dept.description = form.description.data
        db.session.commit()
        flash('Department updated successfully', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', title='Edit Department', form=form)


@admin_bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@admin_required
def delete_department(dept_id):
    form = ConfirmDeleteForm()
    dept = Department.query.get_or_404(dept_id)
    if form.validate_on_submit():
        if dept.courses:
            flash('Cannot delete department with existing courses. Remove or reassign courses first.', 'danger')
        else:
            db.session.delete(dept)
            db.session.commit()
            flash('Department deleted', 'info')
    else:
        flash('Invalid deletion request', 'danger')
    return redirect(url_for('admin.departments'))


@admin_bp.route('/sections')
@admin_required
def sections():
    """List and filter sections."""
    course_id = request.args.get('course_id', type=int) or request.args.get('course', type=int)
    term = request.args.get('term')
    status = request.args.get('status')
    instructor_id = request.args.get('instructor_id', type=int)
    delivery_mode = request.args.get('delivery_mode')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Distinct terms for autocomplete
    term_rows = CourseSection.query.with_entities(CourseSection.term).distinct().order_by(CourseSection.term.desc()).all()
    term_options = [t[0] for t in term_rows if t and t[0]]

    query = CourseSection.query
    if course_id:
        query = query.filter_by(course_id=course_id)
    if term:
        query = query.filter_by(term=term)
    if status:
        query = query.filter_by(status=status)
    if instructor_id:
        query = query.filter_by(instructor_id=instructor_id)
    if delivery_mode:
        query = query.filter_by(delivery_mode=delivery_mode)

    pagination = query.order_by(CourseSection.term.desc(), CourseSection.section_code).paginate(page=page, per_page=per_page, error_out=False)
    sections = pagination.items
    courses_list = Course.query.order_by(Course.code).all()
    instructors = InstructorProfile.query.all()
    delete_form = ConfirmDeleteForm()
    return render_template('admin/sections.html',
                          title='Manage Sections',
                          sections=sections,
                          courses=courses_list,
                          instructors=instructors,
                          selected_course_id=course_id,
                          term=term,
                          status=status,
                          instructor_id=instructor_id,
                          delivery_mode=delivery_mode,
                          term_options=term_options,
                          pagination=pagination,
                          delete_form=delete_form)


@admin_bp.route('/sections/bulk', methods=['POST'])
@admin_required
def sections_bulk():
    """Bulk actions on sections: open/close/cancel/assign_instructor."""
    action = request.form.get('action')
    selected_ids = request.form.getlist('selected_ids')
    # Convert to ints safely
    try:
        selected_ids = [int(sid) for sid in selected_ids]
    except Exception:
        selected_ids = []
    instructor_id = request.form.get('instructor_id', type=int)
    if not selected_ids:
        flash('No sections selected', 'warning')
        return redirect(url_for('admin.sections'))
    sections = CourseSection.query.filter(CourseSection.id.in_(selected_ids)).all()
    count = 0
    for s in sections:
        if action == 'open':
            s.status = 'Open'
            count += 1
        elif action == 'close':
            s.status = 'Closed'
            count += 1
        elif action == 'cancel':
            s.status = 'Cancelled'
            count += 1
        elif action == 'assign_instructor' and instructor_id:
            s.instructor_id = instructor_id
            count += 1
    db.session.commit()
    flash(f'Bulk action applied to {count} section(s)', 'success')
    # Redirect back to the referring filtered view if possible
    return redirect(request.referrer or url_for('admin.sections'))


# -------- User creation (Admin) --------
@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    form = RegistrationForm()
    # Populate department choices for instructor creation
    from app.models.course import Department
    departments = Department.query.order_by(Department.name).all()
    form.department_id.choices = [(0, 'Unassigned')] + [(d.id, d.name) for d in departments]

    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            is_active=True
        )
        user.set_password(form.password.data)
        # Add the user to the session before manipulating dynamic relationships
        db.session.add(user)
        db.session.flush()  # ensure the user is bound to the session and has an id
        # Assign role
        role_key = form.role.data
        role_name = Role.STUDENT if role_key == 'student' else Role.INSTRUCTOR
        role = Role.query.filter_by(name=role_name).first()
        if role:
            user.add_role(role)
        db.session.commit()

        # Create minimal profile as required
        from datetime import date
        if role_key == 'student':
            # Generate a unique student number
            student_number = f"S{100000 + user.id}"
            profile = StudentProfile(user_id=user.id, student_number=student_number, enrollment_year=date.today().year)
            db.session.add(profile)
        else:
            employee_number = f"E{100000 + user.id}"
            dept_val = form.department_id.data or 0
            profile = InstructorProfile(
                user_id=user.id,
                employee_number=employee_number,
                hire_date=date.today(),
                department_id=(None if dept_val == 0 else dept_val)
            )
            db.session.add(profile)
        db.session.commit()

        flash('User created successfully', 'success')
        return redirect(url_for('admin.users'))

    if not departments:
        flash('No departments found. You can add some under Admin > Departments. Instructor department is optional.', 'info')

    return render_template('admin/user_form.html', title='Create User', form=form)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = AdminUserEditForm(obj=user)
    # Populate roles choices dynamically
    all_roles = Role.query.order_by(Role.name).all()
    form.roles.choices = [(r.name, r.name) for r in all_roles]
    if request.method == 'GET':
        try:
            form.roles.data = [r.name for r in user.roles.all()]
        except Exception:
            form.roles.data = [r.name for r in user.roles]
    if form.validate_on_submit():
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        # Update roles
        user.roles = []
        for role_name in form.roles.data:
            role_obj = Role.query.filter_by(name=role_name).first()
            if role_obj:
                user.add_role(role_obj)
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', title='Edit User', form=form, user=user)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    form = ConfirmDeleteForm()
    if form.validate_on_submit():
        user = User.query.get_or_404(user_id)
        # Soft delete: deactivate user
        user.is_active = False
        db.session.commit()
        flash('User deactivated', 'info')
    else:
        flash('Invalid deletion request', 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    """Approve a newly registered user and create required profile/IDs if missing."""
    form = ConfirmDeleteForm()
    if not form.validate_on_submit():
        flash('Invalid approval request', 'danger')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    if user.is_active:
        flash('User is already active', 'info')
        return redirect(url_for('admin.users'))

    user.is_active = True

    # Ensure role-based profile exists and assign identifiers
    from datetime import datetime, date
    created_any = False
    if user.is_student():
        if not user.student_profile:
            student_number = f"S{datetime.now().year}{user.id:05d}"
            profile = StudentProfile(
                user_id=user.id,
                student_number=student_number,
                enrollment_year=datetime.now().year,
                academic_status='Active'
            )
            db.session.add(profile)
            created_any = True
    if user.is_instructor():
        if not user.instructor_profile:
            employee_number = f"E{datetime.now().year}{user.id:05d}"
            profile = InstructorProfile(
                user_id=user.id,
                employee_number=employee_number,
                hire_date=date.today(),
            )
            db.session.add(profile)
            created_any = True

    db.session.commit()

    # Notify the user of approval and create an admin announcement
    try:
        from app.models import Notification, Announcement
        note = Notification(
            user_id=user.id,
            notification_type='system',
            title='Account Approved',
            message='Your account has been approved by an administrator. You can now sign in.',
            action_url=url_for('auth.login')
        )
        db.session.add(note)
        # System announcement to Admins
        ann = Announcement(
            author_id=current_user.id,
            title='User account approved',
            body=f"Account for {user.full_name} ({user.email}) has been approved.",
            announcement_type='System',
            priority='Low',
            target_roles=['Admin']
        )
        db.session.add(ann)
        db.session.commit()
    except Exception:
        pass

    msg = 'User approved and activated.' + (' Profile created.' if created_any else '')
    flash(msg, 'success')
    return redirect(url_for('admin.users'))


# -------- Section Enrollment Management --------
@admin_bp.route('/sections/<int:section_id>/enrollments')
@admin_required
def section_enrollments(section_id):
    section = CourseSection.query.get_or_404(section_id)
    enrolled = Enrollment.query.filter_by(course_section_id=section_id, status='Enrolled').all()
    waitlisted = Enrollment.query.filter_by(course_section_id=section_id, status='Waitlisted').order_by(Enrollment.waitlist_position).all()
    return render_template('admin/section_enrollments.html', title=f"Enrollments for {section.course.code}-{section.section_code}", section=section, enrolled=enrolled, waitlisted=waitlisted)


@admin_bp.route('/enrollments/<int:enrollment_id>/drop', methods=['POST'])
@admin_required
def admin_drop_enrollment(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    enrollment.drop(reason='Dropped by admin')
    db.session.commit()
    flash('Enrollment dropped.', 'info')
    return redirect(request.referrer or url_for('admin.sections'))


@admin_bp.route('/sections/<int:section_id>/promote', methods=['POST'])
@admin_required
def admin_promote_waitlist(section_id):
    section = CourseSection.query.get_or_404(section_id)
    section.promote_from_waitlist()
    db.session.commit()
    flash('Promoted next student from waitlist.', 'success')
    return redirect(request.referrer or url_for('admin.section_enrollments', section_id=section_id))


# -------- Reports (PDF) --------
@admin_bp.route('/reports/courses_by_department.pdf')
@admin_required
def report_courses_by_department():
    """Download a PDF of all courses grouped by department."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    except Exception:
        flash('PDF generation is not available on this server.', 'danger')
        return redirect(url_for('admin.dashboard'))

    buffer = __import__('io').BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = [Paragraph('All Courses by Department', styles['Title']), Spacer(1, 0.2*inch)]

    departments = Department.query.order_by(Department.name).all()
    for dept in departments:
        elements.append(Paragraph(dept.name, styles['Heading2']))
        data = [["Code", "Title", "Credits", "Active"]]
        for c in dept.courses:
            data.append([c.code, c.title, str(c.credits), 'Yes' if c.is_active else 'No'])
        table = Table(data, colWidths=[1.0*inch, 3.5*inch, 0.7*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))

    doc.build(elements)
    buffer.seek(0)
    from flask import send_file
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='courses_by_department.pdf')


@admin_bp.route('/reports/students_per_course.pdf')
@admin_required
def report_students_per_course():
    """Download a PDF of student counts per course (by section)."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    except Exception:
        flash('PDF generation is not available on this server.', 'danger')
        return redirect(url_for('admin.dashboard'))

    buffer = __import__('io').BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = [Paragraph('Students Enrolled per Course Section', styles['Title']), Spacer(1, 0.2*inch)]

    sections = CourseSection.query.join(Course).order_by(Course.code, CourseSection.term.desc(), CourseSection.section_code).all()
    data = [["Course", "Section", "Term", "Enrolled"]]
    for s in sections:
        data.append([s.course.code, s.section_code, s.term, str(s.enrolled_count or 0)])
    table = Table(data, colWidths=[1.2*inch, 0.8*inch, 1.4*inch, 0.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    from flask import send_file
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='students_per_course.pdf')


@admin_bp.route('/reports/instructors_with_courses.pdf')
@admin_required
def report_instructors_with_courses():
    """Download a PDF of instructors with their assigned courses."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    except Exception:
        flash('PDF generation is not available on this server.', 'danger')
        return redirect(url_for('admin.dashboard'))

    buffer = __import__('io').BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = [Paragraph('Instructors with Assigned Courses', styles['Title']), Spacer(1, 0.2*inch)]

    instructors = InstructorProfile.query.order_by(InstructorProfile.id).all()
    data = [["Instructor", "Department", "Courses (most recent term)"]]
    for i in instructors:
        courses = [f"{s.course.code}-{s.section_code} ({s.term})" for s in i.course_sections]
        dept_name = i.department.name if i.department else ''
        data.append([i.user.full_name, dept_name, ", ".join(courses) or 'None'])
    table = Table(data, colWidths=[2.2*inch, 1.6*inch, 3.0*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    from flask import send_file
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name='instructors_with_courses.pdf')

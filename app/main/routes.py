"""Main blueprint routes."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app.main import main_bp
from app.models import Course, CourseSection, Department, Announcement, User
from app.forms import SearchForm


@main_bp.route('/')
@main_bp.route('/index')
def index():
    """Home page."""
    featured_courses = Course.query.filter_by(is_active=True).limit(6).all()
    recent_announcements = Announcement.query.order_by(
        Announcement.created_at.desc()
    ).limit(3).all()
    
    return render_template('main/index.html', 
                         title='Welcome',
                         featured_courses=featured_courses,
                         announcements=recent_announcements)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard."""
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_instructor():
        return redirect(url_for('instructor.dashboard'))
    elif current_user.is_student():
        return redirect(url_for('student.dashboard'))
    else:
        # Default dashboard for users without specific roles
        return render_template('main/dashboard.html', title='Dashboard')


@main_bp.route('/courses')
def courses():
    """Browse all courses with filters."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    department_id = request.args.get('department_id', type=int)
    instructor_id = request.args.get('instructor_id', type=int)
    level = request.args.get('level')
    q = (request.args.get('q') or '').strip()

    query = Course.query.filter_by(is_active=True)

    if department_id:
        query = query.filter_by(department_id=department_id)
    if level:
        query = query.filter_by(level=level)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Course.code.ilike(like)) |
            (Course.title.ilike(like)) |
            (Course.description.ilike(like))
        )
    if instructor_id:
        # Only include courses that have at least one section taught by this instructor
        from app.models.course import CourseSection
        query = query.join(CourseSection, CourseSection.course_id == Course.id).filter(CourseSection.instructor_id == instructor_id)
        query = query.distinct()

    courses = query.order_by(Course.code).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    departments = Department.query.order_by(Department.name).all()
    # Instructors list from InstructorProfile
    from app.models.profile import InstructorProfile
    instructors = InstructorProfile.query.all()

    return render_template('main/courses.html',
                         title='Browse Courses',
                         courses=courses,
                         departments=departments,
                         instructors=instructors,
                         selected_department_id=department_id,
                         selected_instructor_id=instructor_id,
                         q=q,
                         level=level)


@main_bp.route('/course/<int:id>')
def course_detail(id):
    """Course detail page."""
    course = Course.query.get_or_404(id)
    current_sections = CourseSection.query.filter_by(
        course_id=id,
        status='Open'
    ).all()
    
    return render_template('main/course_detail.html',
                         title=course.title,
                         course=course,
                         sections=current_sections)


@main_bp.route('/schedule')
def schedule():
    """Course schedule page with filters and actionable buttons."""
    from datetime import datetime as _dt
    # Filters
    term = request.args.get('term')
    department_id = request.args.get('department_id', type=int)
    time_slot = request.args.get('time')  # morning, afternoon, evening
    search = (request.args.get('q') or '').strip()

    # Data for filters
    departments = Department.query.order_by(Department.name).all()
    term_rows = CourseSection.query.with_entities(CourseSection.term).distinct().order_by(CourseSection.term.desc()).all()
    term_options = [t[0] for t in term_rows if t and t[0]]
    if not term:
        term = term_options[0] if term_options else 'Spring 2025'

    # Base query
    query = CourseSection.query.filter_by(term=term, status='Open').join(Course)

    # Department filter
    if department_id:
        query = query.filter(Course.department_id == department_id)

    # Search filter
    if search:
        like = f"%{search}%"
        query = query.filter((Course.code.ilike(like)) | (Course.title.ilike(like)))

    sections = query.order_by(Course.code).all()

    # Stats for summary cards
    departments_count = Department.query.count()
    total_sections = len(sections)
    # Average capacity utilization
    try:
        ratios = [((s.enrolled_count or 0) / s.capacity) for s in sections if s.capacity and s.capacity > 0]
        avg_capacity = int(round((sum(ratios) / len(ratios)) * 100)) if ratios else 0
    except Exception:
        avg_capacity = 0
    registration_label = 'Open' if any(getattr(s, 'status', '') == 'Open' for s in sections) else 'Closed'

    # Time slot filter (client provided keywords: morning 08-12, afternoon 12-17, evening 17-21)
    def _in_slot(sched, slot):
        try:
            if not sched:
                return False
            start_s = (sched.get('start') if isinstance(sched, dict) else None) or None
            if not start_s:
                return False
            st = _dt.strptime(start_s, '%H:%M').time()
            if slot == 'morning':
                return st >= _dt.strptime('08:00', '%H:%M').time() and st < _dt.strptime('12:00', '%H:%M').time()
            if slot == 'afternoon':
                return st >= _dt.strptime('12:00', '%H:%M').time() and st < _dt.strptime('17:00', '%H:%M').time()
            if slot == 'evening':
                return st >= _dt.strptime('17:00', '%H:%M').time() and st <= _dt.strptime('21:00', '%H:%M').time()
        except Exception:
            return False
        return False

    if time_slot in ('morning', 'afternoon', 'evening'):
        sections = [s for s in sections if _in_slot(s.get_meeting_times(), time_slot)]

    return render_template('main/schedule.html',
                         title='Course Schedule',
                         sections=sections,
                         departments=departments,
                         current_term=term,
                         term_options=term_options,
                         selected_department_id=department_id,
                         search_query=search,
                         time_slot=time_slot,
                         total_sections=total_sections,
                         departments_count=departments_count,
                         avg_capacity=avg_capacity,
                         registration_label=registration_label)


@main_bp.route('/announcements')
def announcements():
    """Announcements filtered by role and course context plus a notifications inbox."""
    page = request.args.get('page', 1, type=int)

    base_q = Announcement.query.order_by(Announcement.published_at.desc())
    all_anns = base_q.all()

    filtered = []
    try:
        if current_user.is_authenticated and current_user.is_admin():
            # Admins can see everything
            filtered = all_anns
        elif current_user.is_authenticated and current_user.is_instructor():
            # Instructors: role-targeted or global, plus announcements for their sections
            instr = current_user.instructor_profile
            section_ids = [s.id for s in instr.course_sections] if instr else []
            for a in all_anns:
                roles = (a.target_roles or ['All'])
                roles_norm = [r.lower() for r in roles]
                if ('all' in roles_norm) or ('instructor' in roles_norm) or (a.course_section_id and a.course_section_id in section_ids):
                    filtered.append(a)
        elif current_user.is_authenticated and current_user.is_student():
            # Students: role-targeted or global, plus announcements for enrolled sections
            student = current_user.student_profile
            from app.models.enrollment import Enrollment
            enrolled_section_ids = [e.course_section_id for e in Enrollment.query.filter_by(student_id=student.id).filter(Enrollment.status.in_(['Enrolled', 'Waitlisted', 'Completed'])).all()] if student else []
            for a in all_anns:
                roles = (a.target_roles or ['All'])
                roles_norm = [r.lower() for r in roles]
                if ('all' in roles_norm) or ('student' in roles_norm) or (a.course_section_id and a.course_section_id in enrolled_section_ids):
                    filtered.append(a)
        else:
            # Anonymous users: only globals
            for a in all_anns:
                roles = (a.target_roles or ['All'])
                roles_norm = [r.lower() for r in roles]
                if 'all' in roles_norm:
                    filtered.append(a)
    except Exception:
        filtered = all_anns

    # Paginate the filtered list manually
    per_page = 10
    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = filtered[start:end]

    class _Pagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page
        
        @property
        def has_next(self):
            return self.page < self.pages
        
        @property
        def has_prev(self):
            return self.page > 1

    announcements = _Pagination(page_items, page, per_page, total)

    # Recent notifications for the current user (if logged in)
    notifications = []
    if current_user.is_authenticated:
        try:
            from app.models import Notification
            notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(20).all()
        except Exception:
            notifications = []

    return render_template('main/announcements.html',
                         title='Announcements',
                         announcements=announcements,
                         notifications=notifications)


@main_bp.route('/announcement/<int:id>')
def announcement_detail(id):
    """Announcement detail page."""
    announcement = Announcement.query.get_or_404(id)
    return render_template('main/announcement_detail.html',
                         title=announcement.title,
                         announcement=announcement)


@main_bp.route('/search')
def search():
    """Global search."""
    query = request.args.get('q', '')
    category = request.args.get('category', 'all')
    
    results = {
        'courses': [],
        'users': [],
        'announcements': []
    }
    
    if query:
        if category in ['all', 'courses']:
            results['courses'] = Course.query.filter(
                (Course.code.ilike(f'%{query}%')) |
                (Course.title.ilike(f'%{query}%')) |
                (Course.description.ilike(f'%{query}%'))
            ).limit(10).all()
        
        if category in ['all', 'users'] and current_user.is_authenticated:
            # Only allow user search for authenticated users
            results['users'] = User.query.filter(
                (User.first_name.ilike(f'%{query}%')) |
                (User.last_name.ilike(f'%{query}%')) |
                (User.email.ilike(f'%{query}%'))
            ).limit(10).all()
        
        if category in ['all', 'announcements']:
            results['announcements'] = Announcement.query.filter(
                (Announcement.title.ilike(f'%{query}%')) |
                (Announcement.body.ilike(f'%{query}%'))
            ).limit(10).all()
    
    return render_template('main/search.html',
                         title='Search Results',
                         query=query,
                         category=category,
                         results=results)


@main_bp.route('/profile')
@login_required
def profile():
    """View user profile, redirecting to role-specific pages."""
    if current_user.is_admin():
        return redirect(url_for('admin.profile'))
    if current_user.is_instructor():
        return redirect(url_for('instructor.profile'))
    if current_user.is_student():
        return redirect(url_for('student.profile'))
    # Fallback generic profile
    return render_template('main/profile.html',
                         title='My Profile',
                         user=current_user)


@main_bp.route('/about')
def about():
    """About page."""
    return render_template('main/about.html', title='About Us')


@main_bp.route('/contact')
def contact():
    """Contact page."""
    return render_template('main/contact.html', title='Contact Us')


@main_bp.route('/help')
def help():
    """Help page."""
    return render_template('main/help.html', title='Help & Support')


@main_bp.route('/notifications')
@login_required
def notifications_center():
    """Notifications center with optional unread filter."""
    from app.models import Notification
    filter_q = request.args.get('filter')  # 'unread' or 'all'
    query = Notification.query.filter_by(user_id=current_user.id)
    if filter_q == 'unread':
        query = query.filter_by(is_read=False)
    notes = query.order_by(Notification.created_at.desc()).all()
    return render_template('main/notifications.html', title='Notifications', notifications=notes, filter_q=filter_q)


@main_bp.route('/notifications/<int:note_id>/read', methods=['POST'])
@login_required
def notifications_mark_read(note_id):
    from app.models import Notification
    note = Notification.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    note.mark_as_read()
    db.session.commit()
    flash('Notification marked as read', 'success')
    next_url = request.form.get('next') or url_for('main.notifications_center')
    return redirect(next_url)


@main_bp.route('/health')
def health():
    """Health check endpoint for monitoring."""
    return {'status': 'healthy'}, 200


@main_bp.route('/students')
def students_alias():
    """Convenience alias to the student dashboard."""
    if not current_user.is_authenticated:
        flash('Please log in to view your student dashboard.', 'info')
        return redirect(url_for('auth.login', next=url_for('student.dashboard')))
    if current_user.is_student():
        return redirect(url_for('student.dashboard'))
    flash('Student dashboard is only available to student accounts.', 'warning')
    return redirect(url_for('main.dashboard'))

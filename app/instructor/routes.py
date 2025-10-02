"""Instructor blueprint routes."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.instructor import instructor_bp
from app.models import (CourseSection, Enrollment, Assignment, 
                       Submission, InstructorProfile)
from app.forms import AssignmentForm, GradeForm, AnnouncementForm, InstructorProfileForm
from app.services.grade_service import GradeService


def instructor_required(f):
    """Decorator to require instructor role."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_instructor():
            flash('You must be an instructor to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@instructor_bp.route('/')
@instructor_required
def instructor_root():
    return redirect(url_for('instructor.dashboard'))


@instructor_bp.route('/dashboard')
@instructor_required
def dashboard():
    """Instructor dashboard showing all assigned sections."""
    instructor = current_user.instructor_profile
    
    # All sections taught by this instructor (no term filter)
    sections = CourseSection.query.filter_by(
        instructor_id=instructor.id
    ).order_by(CourseSection.term.desc(), CourseSection.section_code).all()
    
    # Annotate with enrolled for template compatibility
    for s in sections:
        try:
            setattr(s, 'enrolled', s.enrolled_count or 0)
        except Exception:
            pass
    
    # Recent submissions (limit per section)
    recent_submissions = []
    for section in sections:
        submissions = db.session.query(Submission).join(Assignment).filter(
            Assignment.course_section_id == section.id,
            Submission.graded_at.is_(None)
        ).limit(5).all()
        recent_submissions.extend(submissions)
    
    return render_template('instructor/dashboard.html',
                         title='Instructor Dashboard',
                         instructor=instructor,
                         courses=sections,
                         submissions=recent_submissions)


@instructor_bp.route('/courses')
@instructor_required
def courses():
    """View instructor's courses."""
    instructor = current_user.instructor_profile
    sections = CourseSection.query.filter_by(instructor_id=instructor.id).all()
    
    return render_template('instructor/courses.html',
                         title='My Courses',
                         sections=sections)


@instructor_bp.route('/course/<int:id>')
@instructor_required
def course_detail(id):
    """View course section details."""
    section = CourseSection.query.get_or_404(id)
    
    # Verify instructor owns this section
    if section.instructor_id != current_user.instructor_profile.id:
        flash('You are not the instructor for this course.', 'danger')
        return redirect(url_for('instructor.courses'))
    
    enrollments = Enrollment.query.filter_by(course_section_id=id).all()
    assignments = Assignment.query.filter_by(course_section_id=id).all()
    
    return render_template('instructor/course_detail.html',
                         title=section.course.title,
                         section=section,
                         enrollments=enrollments,
                         assignments=assignments)


@instructor_bp.route('/students/<int:section_id>')
@instructor_required
def students(section_id):
    """View enrolled students with pagination."""
    section = CourseSection.query.get_or_404(section_id)
    if section.instructor_id != current_user.instructor_profile.id:
        flash('You are not the instructor for this course.', 'danger')
        return redirect(url_for('instructor.courses'))
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    query = Enrollment.query.filter_by(course_section_id=section_id)
    pagination = query.order_by(Enrollment.enrolled_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    enrollments = pagination.items
    
    return render_template('instructor/students.html',
                         title='Enrolled Students',
                         section=section,
                         enrollments=enrollments,
                         pagination=pagination)


@instructor_bp.route('/roster/<int:section_id>')
@instructor_required
def roster(section_id):
    """View roster with grade entry."""
    section = CourseSection.query.get_or_404(section_id)
    
    # Verify instructor owns this section
    if section.instructor_id != current_user.instructor_profile.id:
        flash('You are not the instructor for this course.', 'danger')
        return redirect(url_for('instructor.courses'))
    
    # Get gradable enrollments
    enrollments = GradeService.get_gradable_enrollments(section_id)
    
    # Get grading summary
    summary = GradeService.get_grading_summary(section_id)
    
    # Get grade distribution
    distribution = GradeService.get_grade_distribution(section_id)
    
    return render_template('instructor/roster.html',
                         title=f'Roster - {section.course.code}',
                         section=section,
                         enrollments=enrollments,
                         summary=summary,
                         distribution=distribution,
                         valid_grades=GradeService.VALID_GRADES)


@instructor_bp.route('/set_grade/<int:enrollment_id>', methods=['POST'])
@instructor_required
def set_grade(enrollment_id):
    """Set grade for a student."""
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    
    # Verify instructor owns this section
    if enrollment.course_section.instructor_id != current_user.instructor_profile.id:
        flash('You cannot grade students in sections you do not teach.', 'danger')
        return redirect(url_for('instructor.courses'))
    
    grade = request.form.get('grade', '').strip()
    
    if not grade:
        flash('Grade cannot be empty', 'danger')
        return redirect(url_for('instructor.roster', section_id=enrollment.course_section_id))
    
    # Set grade using service
    success, messages = GradeService.set_grade(
        enrollment, 
        grade, 
        grader_id=current_user.id
    )
    
    # Flash messages
    category = 'success' if success else 'danger'
    for msg in messages:
        flash(msg, category)
    
    # Redirect back to roster
    return redirect(url_for('instructor.roster', section_id=enrollment.course_section_id))


@instructor_bp.route('/announcements')
@instructor_required
def announcements():
    """Instructor announcements filtered to instructor and their sections."""
    from app.models import Announcement
    instructor = current_user.instructor_profile
    # Sections taught by this instructor
    section_ids = [s.id for s in instructor.course_sections] if instructor else []

    # Fetch and filter announcements
    anns = Announcement.query.order_by(Announcement.published_at.desc()).all()
    filtered = []
    for a in anns:
        # Role targeting (JSON list in target_roles). If None, treat as all roles
        roles = a.target_roles or ['All']
        roles_norm = [r.lower() for r in roles]
        if 'admin' in roles_norm and 'instructor' not in roles_norm and 'all' not in roles_norm:
            # admin-only
            continue
        if ('instructor' in roles_norm) or ('all' in roles_norm) or (not roles):
            # Course scoping: either no course_section_id (global) or belongs to instructor's sections
            if not a.course_section_id or a.course_section_id in section_ids:
                filtered.append(a)
    return render_template('instructor/announcements.html', title='Announcements', announcements=filtered)


@instructor_bp.route('/roster_pdf/<int:section_id>')
@instructor_required
def roster_pdf(section_id):
    """Download a Course Roster PDF for a section."""
    section = CourseSection.query.get_or_404(section_id)
    if section.instructor_id != current_user.instructor_profile.id:
        flash('You are not the instructor for this course.', 'danger')
        return redirect(url_for('instructor.courses'))

    # Generate PDF roster via ReportLab
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_CENTER
        from io import BytesIO
    except Exception:
        flash('PDF generation is not available on this server.', 'danger')
        return redirect(url_for('instructor.roster', section_id=section_id))

    from app.services.grade_service import GradeService
    enrollments = GradeService.get_section_roster(section_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)

    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER, textColor=colors.HexColor('#003366'))

    elements.append(Paragraph('COURSE ROSTER', title_style))
    elements.append(Paragraph(f"{section.course.code} - {section.course.title}", styles['Heading2']))
    elements.append(Paragraph(f"Section {section.section_code} • {section.term} • Instructor: {section.instructor.user.full_name if section.instructor else 'TBA'}", styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))

    data = [["Student ID", "Full Name", "Email", "Enrolled On", "Grade"]]
    for e in enrollments:
        data.append([
            e.student.student_number,
            e.student.user.full_name,
            e.student.user.email,
            e.enrolled_at.strftime('%Y-%m-%d') if e.enrolled_at else '-',
            e.grade or 'Unavailable'
        ])

    table = Table(data, colWidths=[1.2*inch, 2.2*inch, 2.4*inch, 1.0*inch, 0.9*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.whitesmoke, colors.lightgrey]),
    ]))

    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    from flask import send_file
    filename = f"roster_{section.course.code}_{section.section_code}_{section.term.replace(' ', '')}.pdf"
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)


@instructor_bp.route('/inbox')
@instructor_required
def inbox_redirect():
    return redirect(url_for('main.notifications_center'))


@instructor_bp.route('/bulk_grades/<int:section_id>', methods=['POST'])
@instructor_required
def bulk_grades(section_id):
    """Set grades for multiple students."""
    section = CourseSection.query.get_or_404(section_id)
    
    # Verify instructor owns this section
    if section.instructor_id != current_user.instructor_profile.id:
        flash('You cannot grade students in sections you do not teach.', 'danger')
        return redirect(url_for('instructor.courses'))
    
    # Parse form data
    enrollment_grades = []
    for key, value in request.form.items():
        if key.startswith('grade_'):
            enrollment_id = int(key.replace('grade_', ''))
            grade = value.strip()
            if grade:  # Only process non-empty grades
                enrollment = Enrollment.query.get(enrollment_id)
                if enrollment:
                    enrollment_grades.append((enrollment, grade))
    
    if not enrollment_grades:
        flash('No grades to submit', 'warning')
        return redirect(url_for('instructor.roster', section_id=section_id))
    
    # Bulk set grades
    success_count, fail_count, messages = GradeService.bulk_set_grades(
        enrollment_grades,
        grader_id=current_user.id
    )
    
    # Flash messages
    if success_count > 0:
        flash(f'Successfully set {success_count} grades', 'success')
    if fail_count > 0:
        flash(f'Failed to set {fail_count} grades', 'danger')
        for msg in messages[1:]:  # Skip the summary message
            flash(msg, 'warning')
    
    return redirect(url_for('instructor.roster', section_id=section_id))


@instructor_bp.route('/grade/<int:submission_id>', methods=['GET', 'POST'])
@instructor_required
def grade_submission(submission_id):
    """Grade a submission."""
    submission = Submission.query.get_or_404(submission_id)
    form = GradeForm()
    
    if form.validate_on_submit():
        submission.score = form.score.data
        submission.feedback = form.feedback.data
        submission.grade()
        db.session.commit()
        
        flash('Grade saved successfully!', 'success')
        return redirect(url_for('instructor.course_detail', 
                              id=submission.assignment.course_section_id))
    
    return render_template('instructor/grade.html',
                         title='Grade Submission',
                         submission=submission,
                         form=form)


@instructor_bp.route('/profile', methods=['GET', 'POST'])
@instructor_required
def profile():
    """Update instructor profile."""
    form = InstructorProfileForm(obj=current_user.instructor_profile)

    if form.validate_on_submit():
        profile = current_user.instructor_profile
        form.populate_obj(profile)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('instructor.profile'))

    return render_template('instructor/profile.html',
                         title='My Profile',
                         form=form)

"""Student blueprint routes."""

from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from app import db
from datetime import datetime
from app.student import student_bp
from app.models import (Course, CourseSection, Enrollment, 
                       Assignment, Submission, StudentProfile)
from app.forms import EnrollmentForm, SubmissionForm, ProfileForm, StudentProfileForm
from app.services.enrollment_service import (enroll_student, drop_enrollment, 
                                          get_available_sections, get_student_enrollments,
                                          get_enrollment_summary)
from app.services.transcript_service import TranscriptService
from app.models.course import Department
from app.models.transcript import TranscriptRequest
from app.models.enrollment import EnrollmentStatus


def student_required(f):
    """Decorator to require student role."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_student():
            flash('You must be a student to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@student_bp.route('/')
@student_required
def student_root():
    return redirect(url_for('student.dashboard'))


@student_bp.route('/dashboard')
@student_required
def dashboard():
    """Student dashboard."""
    student = current_user.student_profile
    
    # Current enrollments
    current_enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        status='Enrolled'
    ).all()
    
    # Upcoming assignments
    upcoming_assignments = []
    for enrollment in current_enrollments:
        assignments = Assignment.query.filter_by(
            course_section_id=enrollment.course_section_id
        ).filter(Assignment.due_date >= db.func.current_date()).all()
        upcoming_assignments.extend(assignments)
    
    # Recent announcements
    announcements = []
    for enrollment in current_enrollments:
        section_announcements = enrollment.course_section.announcements if hasattr(enrollment.course_section, 'announcements') else []
        announcements.extend(section_announcements)
    
    return render_template('student/dashboard.html',
                         title='Student Dashboard',
                         student=student,
                         student_profile=student,
                         enrollments=current_enrollments,
                         assignments=upcoming_assignments,
                         announcements=announcements)


@student_bp.route('/courses')
@student_required
def courses():
    """View enrolled courses."""
    student = current_user.student_profile
    term = request.args.get('term')
    
    # Get enrollments by status
    current = get_student_enrollments(student, status='enrolled', term=term)
    waitlisted = get_student_enrollments(student, status='waitlisted', term=term)
    completed = get_student_enrollments(student, status='completed', term=term)
    
    # Get enrollment summary
    summary = get_enrollment_summary(student, term=term)
    
    return render_template('student/my_courses.html',
                         title='My Courses',
                         current=current,
                         waitlisted=waitlisted,
                         completed=completed,
                         summary=summary,
                         term=term)


@student_bp.route('/browse')
@student_required
def browse():
    """Browse available courses for enrollment."""
    student = current_user.student_profile
    
    # Get filter parameters
    term = request.args.get('term', 'Spring 2025')
    department_id = request.args.get('department_id', type=int)
    search = request.args.get('search', '').strip()
    
    # Get available sections
    sections = get_available_sections(term=term, department_id=department_id, search=search)
    
    # Get departments for filter
    departments = Department.query.order_by(Department.name).all()
    
    # Get available terms
    terms = db.session.query(CourseSection.term).distinct().order_by(CourseSection.term.desc()).limit(5).all()
    term_options = [t[0] for t in terms]
    
    return render_template('student/browse_courses.html',
                         title='Browse Courses',
                         sections=sections,
                         departments=departments,
                         term_options=term_options,
                         selected_term=term,
                         selected_department_id=department_id,
                         search_query=search)


@student_bp.route('/course/<int:course_id>')
@student_required
def course_detail(course_id):
    """View course details and available sections."""
    course = Course.query.get_or_404(course_id)
    student = current_user.student_profile
    
    # Get available sections for this course
    sections = CourseSection.query.filter_by(
        course_id=course_id,
        status='Open'
    ).order_by(CourseSection.term.desc(), CourseSection.section_code).all()
    
    # Prerequisites: not enforced and not displayed
    prerequisites_met = True
    missing_prereqs = []
    
    # Get already enrolled sections for this course
    enrolled_sections = Enrollment.query.filter_by(
        student_id=student.id
    ).join(CourseSection).filter(
        CourseSection.course_id == course_id,
        Enrollment.status.in_(['Enrolled', 'Waitlisted'])
    ).all()
    
    return render_template('student/course_detail.html',
                         title=course.title,
                         course=course,
                         sections=sections,
                         prerequisites_met=prerequisites_met,
                         missing_prereqs=missing_prereqs,
                         enrolled_sections=enrolled_sections)


@student_bp.route('/enroll/<int:section_id>', methods=['POST'])
@student_required
def enroll(section_id):
    """Enroll in a course section."""
    student = current_user.student_profile
    section = CourseSection.query.get_or_404(section_id)
    
    # Use enrollment service with robust error handling
    try:
        enrollment, success, messages = enroll_student(student, section)
    except Exception:
        from flask import current_app
        current_app.logger.exception('Error during enrollment for student_id=%s section_id=%s', student.id, section.id)
        enrollment, success, messages = None, False, ['Enrollment failed due to an unexpected error. Please try again.']
    
    # Flash messages
    if success:
        for msg in messages:
            flash(msg, 'success')
    else:
        for msg in messages:
            flash(msg, 'danger')
    
    # Redirect back to where they came from or course detail
    next_page = request.args.get('next') or request.referrer or url_for('student.browse')
    return redirect(next_page)


@student_bp.route('/drop/<int:enrollment_id>', methods=['POST'])
@student_required
def drop(enrollment_id):
    """Drop a course."""
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    
    # Verify this enrollment belongs to the current student
    if enrollment.student_id != current_user.student_profile.id:
        flash('You can only drop your own courses.', 'danger')
        return redirect(url_for('student.courses'))
    
    # Use drop service
    success, messages = drop_enrollment(enrollment, reason='Student requested drop')
    
    # Flash messages
    category = 'success' if success else 'danger'
    for msg in messages:
        flash(msg, category)
    
    return redirect(url_for('student.courses'))


@student_bp.route('/schedule')
@student_required
def schedule():
    """View class schedule."""
    student = current_user.student_profile
    term = request.args.get('term', 'Spring 2025')
    
    enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        status='Enrolled'
    ).join(CourseSection).filter(
        CourseSection.term == term
    ).all()
    
    return render_template('student/schedule.html',
                         title='My Schedule',
                         enrollments=enrollments,
                         term=term)


@student_bp.route('/inbox')
@student_required
def inbox():
    """Student notifications inbox."""
    from app.models import Notification
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('student/inbox.html', title='Inbox', notifications=notes)


@student_bp.route('/grades')
@student_required
def grades():
    """View grades."""
    student = current_user.student_profile
    
    # Get all enrollments (graded and ungraded)
    all_enrollments = Enrollment.query.filter_by(
        student_id=student.id
    ).filter(
        Enrollment.status.in_(['Enrolled', 'Completed', 'Failed'])
    ).join(CourseSection).order_by(CourseSection.term.desc()).all()
    
    # Calculate GPA
    student.calculate_gpa()
    
    return render_template('student/grades.html',
                         title='My Grades',
                         enrollments=all_enrollments,
                         student=student)


@student_bp.route('/assignments')
@student_required
def assignments():
    """View all assignments."""
    student = current_user.student_profile
    
    # Get all enrolled sections
    enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        status=EnrollmentStatus.ENROLLED
    ).all()
    
    all_assignments = []
    for enrollment in enrollments:
        assignments = Assignment.query.filter_by(
            course_section_id=enrollment.course_section_id
        ).all()
        for assignment in assignments:
            # Check if submitted
            submission = Submission.query.filter_by(
                assignment_id=assignment.id,
                student_id=student.id
            ).first()
            assignment.submission = submission
            # Compute overdue flag safely
            try:
                assignment.is_overdue = bool(assignment.due_date and assignment.due_date < datetime.utcnow())
            except Exception:
                assignment.is_overdue = False
            all_assignments.append(assignment)
    
    return render_template('student/assignments.html',
                         title='Assignments',
                         assignments=all_assignments)


@student_bp.route('/assignment/<int:id>')
@student_required
def assignment_detail(id):
    """View assignment details."""
    assignment = Assignment.query.get_or_404(id)
    student = current_user.student_profile
    
    # Verify student is enrolled in this course
    enrollment = Enrollment.query.filter_by(
        student_id=student.id,
        course_section_id=assignment.course_section_id,
        status=EnrollmentStatus.ENROLLED
    ).first()
    
    if not enrollment:
        flash('You are not enrolled in this course.', 'danger')
        return redirect(url_for('student.assignments'))
    
    submission = Submission.query.filter_by(
        assignment_id=id,
        student_id=student.id
    ).first()
    
    return render_template('student/assignment_detail.html',
                         title=assignment.title,
                         assignment=assignment,
                         submission=submission)


@student_bp.route('/submit/<int:assignment_id>', methods=['GET', 'POST'])
@student_required
def submit_assignment(assignment_id):
    """Submit an assignment."""
    assignment = Assignment.query.get_or_404(assignment_id)
    student = current_user.student_profile
    form = SubmissionForm()
    
    if form.validate_on_submit():
        submission = Submission(
            assignment_id=assignment_id,
            student_id=student.id,
            submission_text=form.content.data,
            feedback=form.notes.data
        )
        submission.submit()
        db.session.add(submission)
        db.session.commit()
        
        flash('Assignment submitted successfully!', 'success')
        return redirect(url_for('student.assignment_detail', id=assignment_id))
    
    return render_template('student/submit_assignment.html',
                         title='Submit Assignment',
                         form=form,
                         assignment=assignment)


@student_bp.route('/transcript')
@student_required
def transcript():
    """View transcript page with download option."""
    student = current_user.student_profile
    
    return render_template('student/transcript.html',
                         title='My Transcript',
                         student=student)


@student_bp.route('/transcript/download')
@student_required
def download_transcript():
    """Download unofficial transcript as PDF."""
    student = current_user.student_profile
    
    try:
        # Generate PDF transcript
        pdf_buffer = TranscriptService.generate_transcript(
            student_profile=student,
            official=False
        )
        
        # Generate filename
        filename = TranscriptService.generate_filename(
            student_profile=student,
            official=False
        )
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'Error generating transcript: {str(e)}', 'danger')
        return redirect(url_for('student.transcript'))


@student_bp.route('/transcript/official/request', methods=['POST'])
@student_required
def request_official_transcript():
    """Create a transcript request for registrar approval."""
    student = current_user.student_profile
    # Check for existing pending request
    existing = TranscriptRequest.query.filter_by(student_id=student.id, status='Pending').first()
    if existing:
        flash('You already have a pending transcript request.', 'warning')
        return redirect(url_for('student.transcript'))
    # Create a new request
    tr = TranscriptRequest(student_id=student.id, status='Pending')
    db.session.add(tr)
    db.session.commit()
    flash('Official transcript request submitted. The Registrar will review it shortly.', 'success')
    return redirect(url_for('student.transcript'))


@student_bp.route('/transcript/official/download')
@student_required
def download_official_transcript():
    """Download official transcript as PDF if approved."""
    student = current_user.student_profile
    # Require an approved request
    approved = TranscriptRequest.query.filter_by(student_id=student.id, status='Approved').order_by(TranscriptRequest.processed_at.desc()).first()
    if not approved:
        flash('Official transcript requires Registrar approval. Please submit a request first.', 'warning')
        return redirect(url_for('student.transcript'))
    try:
        # Generate PDF transcript
        pdf_buffer = TranscriptService.generate_transcript(
            student_profile=student,
            official=True
        )
        
        # Generate filename
        filename = TranscriptService.generate_filename(
            student_profile=student,
            official=True
        )
        # Mark as issued
        approved.mark_issued(filename=filename)
        db.session.commit()
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'Error generating official transcript: {str(e)}', 'danger')
        return redirect(url_for('student.transcript'))


@student_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    """Update student profile."""
    form = StudentProfileForm(obj=current_user.student_profile)
    
    if form.validate_on_submit():
        profile = current_user.student_profile
        form.populate_obj(profile)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.profile'))
    
    return render_template('student/profile.html',
                         title='My Profile',
                         form=form)


@student_bp.route('/registration-proof')
@student_required
def registration_proof():
    """Download proof of registration as PDF for the current student."""
    return _registration_proof_for_student(current_user.student_profile)


@student_bp.route('/registration-proof/<int:student_id>')
@login_required
def registration_proof_for_admin(student_id):
    """Admin can download proof of registration for a specific student."""
    if not current_user.is_admin():
        flash('Not authorized', 'danger')
        return redirect(url_for('main.index'))
    from app.models.profile import StudentProfile
    student = StudentProfile.query.get_or_404(student_id)
    return _registration_proof_for_student(student)


def _registration_proof_for_student(student):
    # Check if student is approved/active
    if (not student or not getattr(student, 'user', None)
            or not student.user.is_active or student.academic_status != 'Active'):
        # Still generate a PDF with header but note inactive status
        status_note = 'Inactive or not approved'
    else:
        status_note = None

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        )
        from reportlab.lib.enums import TA_CENTER
        from io import BytesIO
    except ImportError:
        flash('PDF generation is not available. Please contact support.', 'danger')
        return redirect(url_for('student.dashboard'))

    # Get current enrollments
    current_enrollments = Enrollment.query.filter_by(
        student_id=student.id,
        status='Enrolled'
    ).join(CourseSection).order_by(CourseSection.term.desc()).all()

    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#003366'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    elements.append(Paragraph("PROOF OF REGISTRATION", title_style))
    elements.append(Paragraph("University Registration System", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))

    # Student Information
    student_data = [
        ["Student Name:", f"{student.user.first_name} {student.user.last_name}"],
        ["Student Number:", student.student_number],
        ["Program:", student.program or "Not specified"],
        ["Academic Status:", student.academic_status],
        ["Date Issued:", datetime.now().strftime('%B %d, %Y')]
    ]

    student_table = Table(student_data, colWidths=[2*inch, 4*inch])
    student_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    elements.append(student_table)
    elements.append(Spacer(1, 0.4*inch))

    # Current Enrollments
    elements.append(Paragraph("CURRENT ENROLLMENTS", styles['Heading2']))
    elements.append(Spacer(1, 0.2*inch))

    if not current_enrollments:
        elements.append(Paragraph("No courses enrolled", styles['Normal']))
    else:
        # Group by term
        terms_dict = {}
        for enrollment in current_enrollments:
            term = enrollment.course_section.term
            if term not in terms_dict:
                terms_dict[term] = []
            terms_dict[term].append(enrollment)

        for term in sorted(terms_dict.keys(), reverse=True):
            elements.append(Paragraph(f"<b>{term}</b>", styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))

            course_data = [["Course Code", "Course Title", "Section", "Credits", "Instructor"]]

            for enrollment in terms_dict[term]:
                course_data.append([
                    enrollment.course_section.course.code,
                    enrollment.course_section.course.title[:35],
                    enrollment.course_section.section_code,
                    str(enrollment.course_section.course.credits),
                    enrollment.course_section.instructor.user.full_name if enrollment.course_section.instructor else 'TBA'
                ])

            course_table = Table(course_data, colWidths=[1*inch, 2.5*inch, 0.7*inch, 0.7*inch, 1.6*inch])
            course_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))

            elements.append(course_table)
            elements.append(Spacer(1, 0.3*inch))

        # Total Credits
        total_credits = sum(e.course_section.course.credits for e in current_enrollments)
        elements.append(Paragraph(f"<b>Total Credits Enrolled: {total_credits}</b>", styles['Normal']))
        elements.append(Spacer(1, 0.4*inch))

    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    footer_text = (
        f"Issued on {datetime.now().strftime('%B %d, %Y')}. "
        + ("Status: " + status_note + ". " if status_note else "")
        + "This document lists the student's current enrollments."
    )
    elements.append(Paragraph(footer_text, footer_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    filename = f"registration_proof_{student.student_number}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

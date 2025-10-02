"""Registrar routes for approvals and overrides."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.registrar import registrar_bp
from app.models import (
    User, CourseSection, Enrollment, StudentProfile, AuditLog, TranscriptRequest
)
from app.services.enrollment_service import enroll_student


def registrar_required(f):
    """Decorator to require registrar role."""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_registrar() and not current_user.is_admin():
            flash('You must be a registrar to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@registrar_bp.route('/dashboard')
@registrar_required
def dashboard():
    """Registrar dashboard with key queues and actions."""
    pending_transcripts = TranscriptRequest.query.filter_by(status='Pending').count()
    approved_transcripts = TranscriptRequest.query.filter_by(status='Approved').count()
    issued_transcripts = TranscriptRequest.query.filter_by(status='Issued').count()
    
    # Simple waitlist metric: sections with waitlist_count > 0
    waitlisted_sections = CourseSection.query.filter(CourseSection.waitlist_count > 0).count()

    stats = {
        'pending_transcripts': pending_transcripts,
        'approved_transcripts': approved_transcripts,
        'issued_transcripts': issued_transcripts,
        'waitlisted_sections': waitlisted_sections,
    }

    recent_requests = TranscriptRequest.query.order_by(TranscriptRequest.created_at.desc()).limit(10).all()

    return render_template('registrar/dashboard.html', title='Registrar Dashboard', stats=stats, recent_requests=recent_requests)


@registrar_bp.route('/transcripts')
@registrar_required
def transcript_requests():
    """List and filter transcript requests."""
    status = request.args.get('status', 'Pending')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = TranscriptRequest.query
    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(TranscriptRequest.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    requests_list = pagination.items

    return render_template('registrar/transcript_requests.html', title='Transcript Requests', requests=requests_list, pagination=pagination, status=status)


@registrar_bp.route('/transcripts/<int:req_id>/approve', methods=['POST'])
@registrar_required
def approve_transcript(req_id):
    tr = TranscriptRequest.query.get_or_404(req_id)
    if tr.status not in ['Pending', 'Rejected']:
        flash('Request cannot be approved from current status.', 'warning')
        return redirect(request.referrer or url_for('registrar.transcript_requests'))
    tr.approve(processor_id=current_user.id, notes=request.form.get('notes'))

    # Audit
    audit = AuditLog(
        user_id=current_user.id,
        action='APPROVE',
        entity_type='TranscriptRequest',
        entity_id=tr.id,
        new_values={'status': tr.status},
        endpoint=request.path,
        http_method='POST'
    )
    db.session.add(audit)
    db.session.commit()
    flash('Transcript request approved.', 'success')
    return redirect(request.referrer or url_for('registrar.transcript_requests'))


@registrar_bp.route('/transcripts/<int:req_id>/reject', methods=['POST'])
@registrar_required
def reject_transcript(req_id):
    tr = TranscriptRequest.query.get_or_404(req_id)
    if tr.status not in ['Pending', 'Approved']:
        flash('Request cannot be rejected from current status.', 'warning')
        return redirect(request.referrer or url_for('registrar.transcript_requests'))
    tr.reject(processor_id=current_user.id, notes=request.form.get('notes'))

    # Audit
    audit = AuditLog(
        user_id=current_user.id,
        action='REJECT',
        entity_type='TranscriptRequest',
        entity_id=tr.id,
        new_values={'status': tr.status},
        endpoint=request.path,
        http_method='POST'
    )
    db.session.add(audit)
    db.session.commit()
    flash('Transcript request rejected.', 'info')
    return redirect(request.referrer or url_for('registrar.transcript_requests'))


@registrar_bp.route('/sections/<int:section_id>/promote', methods=['POST'])
@registrar_required
def promote_waitlist(section_id):
    section = CourseSection.query.get_or_404(section_id)
    before = section.enrolled_count or 0
    # Promote one student from waitlist if capacity allows
    section.promote_from_waitlist()
    db.session.commit()

    after = section.enrolled_count or 0
    if after > before:
        flash('Promoted next student from waitlist.', 'success')
    else:
        flash('No promotion performed (section may be full or no waitlisted students).', 'warning')

    # Audit
    audit = AuditLog(
        user_id=current_user.id,
        action='WAITLIST_PROMOTION',
        entity_type='CourseSection',
        entity_id=section.id,
        endpoint=request.path,
        http_method='POST'
    )
    db.session.add(audit)
    db.session.commit()

    return redirect(request.referrer or url_for('registrar.dashboard'))


@registrar_bp.route('/enrollments/override', methods=['POST'])
@registrar_required
def override_enrollment():
    """Force-enroll a student into a section (override checks)."""
    student_user_id = request.form.get('student_user_id', type=int)
    section_id = request.form.get('section_id', type=int)
    if not student_user_id or not section_id:
        flash('Missing student or section.', 'danger')
        return redirect(request.referrer or url_for('registrar.dashboard'))

    student_user = User.query.get_or_404(student_user_id)
    if not student_user.student_profile:
        flash('Selected user is not a student.', 'danger')
        return redirect(request.referrer or url_for('registrar.dashboard'))

    section = CourseSection.query.get_or_404(section_id)

    enrollment, success, messages = enroll_student(
        student_user.student_profile,
        section,
        audit_mode=False,
        override_by=current_user.id
    )
    for msg in messages:
        flash(msg, 'success' if success else 'danger')

    # Audit
    audit = AuditLog(
        user_id=current_user.id,
        action='ENROLL_OVERRIDE' if success else 'ENROLL_OVERRIDE_FAILED',
        entity_type='Enrollment',
        entity_id=enrollment.id if enrollment else None,
        new_values={'section_id': section.id, 'student_id': student_user.student_profile.id} if enrollment else None,
        endpoint=request.path,
        http_method='POST'
    )
    db.session.add(audit)
    db.session.commit()

    return redirect(request.referrer or url_for('registrar.dashboard'))

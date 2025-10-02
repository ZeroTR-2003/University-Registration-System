"""API routes for enrollments."""

from flask import jsonify, request
from flask_jwt_extended import jwt_required, current_user as jwt_current_user
from app.api import api_bp
from app.models import db
from app.models.enrollment import Enrollment
from app.models.course import CourseSection
from app.services.enrollment_service import can_enroll as svc_can_enroll, enroll_student as svc_enroll_student, drop_enrollment as svc_drop_enrollment
from app import limiter


@api_bp.route('/enrollments', methods=['GET'])
@jwt_required()
def list_enrollments():
    """List current user's enrollments (student only)."""
    if not jwt_current_user.is_student() or not jwt_current_user.student_profile:
        return jsonify({'error': 'Student account required'}), 403
    student = jwt_current_user.student_profile
    enrollments = Enrollment.query.filter_by(student_id=student.id).all()
    return jsonify([e.to_dict() for e in enrollments]), 200


@api_bp.route('/enrollments/check', methods=['GET'])
@jwt_required()
@limiter.limit("120 per hour")
def check_enrollment():
    """Check eligibility for a course_section_id."""
    if not jwt_current_user.is_student() or not jwt_current_user.student_profile:
        return jsonify({'error': 'Student account required'}), 403
    section_id = request.args.get('course_section_id', type=int)
    if not section_id:
        return jsonify({'error': 'course_section_id is required'}), 400
    section = CourseSection.query.get_or_404(section_id)
    ok, errors, warnings = Enrollment.can_enroll(jwt_current_user.student_profile, section)
    return jsonify({'eligible': ok, 'errors': errors, 'warnings': warnings}), 200


@api_bp.route('/enrollments', methods=['POST'])
@jwt_required()
@limiter.limit("60 per hour")
def create_enrollment():
    """Enroll current student in a course section."""
    if not jwt_current_user.is_student() or not jwt_current_user.student_profile:
        return jsonify({'error': 'Student account required'}), 403
    data = request.get_json() or {}
    section_id = data.get('course_section_id')
    if not section_id:
        return jsonify({'error': 'course_section_id is required'}), 400
    section = CourseSection.query.get_or_404(section_id)

    student = jwt_current_user.student_profile
    ok, errors, warnings = svc_can_enroll(student, section)
    if not ok:
        return jsonify({'eligible': False, 'errors': errors, 'warnings': warnings}), 400

    enrollment, success, messages = svc_enroll_student(student, section)
    if not success or not enrollment:
        return jsonify({'eligible': False, 'errors': messages}), 400
    return jsonify(enrollment.to_dict()), 201


@api_bp.route('/enrollments/<int:enrollment_id>', methods=['DELETE'])
@jwt_required()
def drop_enrollment(enrollment_id):
    """Drop an enrollment for current student."""
    if not jwt_current_user.is_student() or not jwt_current_user.student_profile:
        return jsonify({'error': 'Student account required'}), 403
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    if enrollment.student_id != jwt_current_user.student_profile.id:
        return jsonify({'error': 'Forbidden'}), 403
    svc_drop_enrollment(enrollment, reason='Dropped via API')
    return '', 204

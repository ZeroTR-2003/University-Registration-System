"""Grades API routes: set grades and view section roster."""

from flask import jsonify, request
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

from app.api import api_bp
from app.models import db
from app.models.enrollment import Enrollment
from app.models.course import CourseSection
from app.services.grade_service import GradeService


def _can_grade(enrollment: Enrollment) -> (bool, str | None):
    # Admins and Registrars can grade
    if jwt_current_user.is_admin() or jwt_current_user.is_registrar():
        return True, None
    # Instructors can grade their own sections
    if jwt_current_user.is_instructor() and jwt_current_user.instructor_profile:
        if enrollment.course_section and enrollment.course_section.instructor_id == jwt_current_user.instructor_profile.id:
            return True, None
        return False, "Not instructor of this section"
    return False, "Insufficient permissions"


@api_bp.route('/enrollments/<int:enrollment_id>/grade', methods=['POST'])
@jwt_required()
def set_enrollment_grade(enrollment_id: int):
    """Set a grade for an enrollment (instructor/admin/registrar).
    ---
    tags:
      - Grades
    parameters:
      - in: path
        name: enrollment_id
        required: true
        schema:
          type: integer
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            grade:
              type: string
              example: A
    responses:
      200:
        description: Grade set successfully
      400:
        description: Validation error
      403:
        description: Forbidden
    """
    enrollment = Enrollment.query.get_or_404(enrollment_id)

    allowed, reason = _can_grade(enrollment)
    if not allowed:
        return jsonify({'error': 'Forbidden', 'reason': reason}), 403

    data = request.get_json() or {}
    grade = data.get('grade')
    if not grade:
        return jsonify({'error': 'grade is required'}), 400

    ok, messages = GradeService.set_grade(enrollment, grade, grader_id=(jwt_current_user.instructor_profile.id if jwt_current_user.is_instructor() and jwt_current_user.instructor_profile else None))
    status = 200 if ok else 400
    return jsonify({'success': ok, 'messages': messages, 'enrollment': enrollment.to_dict()}), status


@api_bp.route('/sections/<int:section_id>/roster', methods=['GET'])
@jwt_required()
def get_section_roster(section_id: int):
    """Get roster of enrollments for a section (instructor/admin/registrar).
    ---
    tags:
      - Grades
    parameters:
      - in: path
        name: section_id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: List of enrollments
      403:
        description: Forbidden
    """
    section = CourseSection.query.get_or_404(section_id)

    # Permission: instructor of section or admin/registrar
    if not (jwt_current_user.is_admin() or jwt_current_user.is_registrar() or (
        jwt_current_user.is_instructor() and jwt_current_user.instructor_profile and section.instructor_id == jwt_current_user.instructor_profile.id
    )):
        return jsonify({'error': 'Forbidden'}), 403

    enrollments = GradeService.get_section_roster(section_id)
    return jsonify([e.to_dict() for e in enrollments]), 200

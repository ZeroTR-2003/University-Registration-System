"""Transcript API endpoints for PDF generation."""

from flask import jsonify, request, send_file
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

from app.api import api_bp
from app.models.user import User
from app.models import db
from app.services.transcript_service import TranscriptService


@api_bp.route('/transcripts/me', methods=['GET'])
@jwt_required()
def transcript_me():
    """Download unofficial transcript for current student.
    ---
    tags:
      - Transcripts
    produces:
      - application/pdf
    responses:
      200:
        description: PDF content
      403:
        description: Student account required
    """
    if not jwt_current_user.is_student() or not jwt_current_user.student_profile:
        return jsonify({'error': 'Student account required'}), 403

    pdf_buffer = TranscriptService.generate_transcript(jwt_current_user.student_profile, official=False)
    filename = TranscriptService.generate_filename(jwt_current_user.student_profile, official=False)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


@api_bp.route('/transcripts/<int:user_id>', methods=['GET'])
@jwt_required()
def transcript_user(user_id: int):
    """Download transcript for a student (admin/registrar).
    Use ?official=true for official transcripts.
    ---
    tags:
      - Transcripts
    parameters:
      - in: path
        name: user_id
        required: true
        schema:
          type: integer
      - in: query
        name: official
        required: false
        schema:
          type: boolean
        description: When true, generate official transcript
    produces:
      - application/pdf
    responses:
      200:
        description: PDF content
      403:
        description: Forbidden
      400:
        description: User is not a student
    """
    # Only admin or registrar can download for others
    if not (jwt_current_user.is_admin() or jwt_current_user.is_registrar()):
        return jsonify({'error': 'Forbidden'}), 403

    user = User.query.get_or_404(user_id)
    if not user.student_profile:
        return jsonify({'error': 'User is not a student'}), 400

    official = str(request.args.get('official', 'true')).lower() in ['1', 'true', 'yes']
    pdf_buffer = TranscriptService.generate_transcript(user.student_profile, official=official)
    filename = TranscriptService.generate_filename(user.student_profile, official=official)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )

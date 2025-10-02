"""API routes for courses."""

from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, current_user as jwt_current_user
from app.api import api_bp
from app.models import Course, CourseSection, Department, db
from app import cache

@api_bp.route('/courses', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def get_courses():
    """Get all courses."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    courses = Course.query.filter_by(is_active=True).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return jsonify({
        'courses': [course.to_dict() for course in courses.items],
        'total': courses.total,
        'page': page,
        'pages': courses.pages
    })


@api_bp.route('/courses/<int:id>', methods=['GET'])
def get_course(id):
    """Get a specific course."""
    course = Course.query.get_or_404(id)
    return jsonify(course.to_dict())


@api_bp.route('/courses', methods=['POST'])
@jwt_required()
def create_course():
    """Create a new course (admin/instructor only).
    ---
    tags:
      - Courses
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              code:
                type: string
              title:
                type: string
              department_id:
                type: integer
              credits:
                type: number
    responses:
      201:
        description: Created
      400:
        description: Bad request
      403:
        description: Forbidden
    """
    if not (jwt_current_user.is_admin() or jwt_current_user.is_instructor()):
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    required = ['code', 'title', 'department_id', 'credits']
    missing = [f for f in required if data.get(f) in (None, '')]
    if missing:
        return jsonify({'error': f"Missing fields: {', '.join(missing)}"}), 400
    
    course = Course(
        code=data['code'],
        title=data['title'],
        description=data.get('description'),
        department_id=data['department_id'],
        credits=data['credits'],
        level=data.get('level', 'Undergraduate')
    )
    
    db.session.add(course)
    db.session.commit()
    
    return jsonify(course.to_dict()), 201


@api_bp.route('/courses/<int:id>', methods=['PUT'])
@jwt_required()
def update_course(id):
    """Update a course.
    ---
    tags:
      - Courses
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: id
        required: true
        schema:
          type: integer
    responses:
      200:
        description: Updated course
      403:
        description: Forbidden
    """
    if not (jwt_current_user.is_admin() or jwt_current_user.is_instructor()):
        return jsonify({'error': 'Forbidden'}), 403
    course = Course.query.get_or_404(id)
    data = request.get_json() or {}
    
    course.title = data.get('title', course.title)
    course.description = data.get('description', course.description)
    course.credits = data.get('credits', course.credits)
    
    db.session.commit()
    
    return jsonify(course.to_dict())


@api_bp.route('/courses/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_course(id):
    """Delete a course (soft delete).
    ---
    tags:
      - Courses
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: id
        required: true
        schema:
          type: integer
    responses:
      204:
        description: Deleted
      403:
        description: Forbidden
    """
    if not jwt_current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    course = Course.query.get_or_404(id)
    course.is_active = False
    db.session.commit()
    
    return '', 204


@api_bp.route('/courses/<int:id>/sections', methods=['GET'])
def get_course_sections(id):
    """Get sections for a course."""
    sections = CourseSection.query.filter_by(course_id=id, status='Open').all()
    return jsonify([{
        'id': s.id,
        'section_code': s.section_code,
        'term': s.term,
        'instructor': s.instructor.user.full_name if s.instructor else None,
        'capacity': s.capacity,
        'enrolled': s.enrolled_count,
        'available': s.capacity - s.enrolled_count
    } for s in sections])

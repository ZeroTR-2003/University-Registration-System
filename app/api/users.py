"""API routes for users."""

from flask import jsonify, request
from flask_jwt_extended import jwt_required, current_user as jwt_current_user
from app.api import api_bp
from app.models import db
from app.models.user import User


@api_bp.route('/users/me', methods=['GET'])
@jwt_required()
def get_me():
    return jsonify(jwt_current_user.to_dict()), 200


@api_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """Get users (admin only)."""
    if not jwt_current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    users = User.query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'users': [u.to_dict() for u in users.items],
        'total': users.total,
        'page': page,
        'pages': users.pages
    }), 200


@api_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """Get a specific user (self or admin)."""
    if jwt_current_user.id != user_id and not jwt_current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200

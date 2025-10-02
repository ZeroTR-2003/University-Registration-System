"""API authentication routes."""

from flask import jsonify, request
from flask_jwt_extended import (
    jwt_required,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    current_user as jwt_current_user
)
from datetime import datetime

from app.api import api_bp
from app.models import db
from app.models.user import User, Role
from app.services.auth_service import register_user, authenticate
from app import limiter


@api_bp.route('/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def api_register():
    """Register a new user (defaults to Student role)."""
    data = request.get_json() or {}
    required = ['email', 'password', 'first_name', 'last_name']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f"Missing fields: {', '.join(missing)}"}), 400
    try:
        user = register_user(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role_name=data.get('role', Role.STUDENT),
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 409
    return jsonify({'message': 'Registration successful', 'user': user.to_dict()}), 201


@api_bp.route('/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def api_login():
    """Login and retrieve JWT access/refresh tokens."""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    user = authenticate(email, password)
    if not user:
        return jsonify({'error': 'Invalid or disallowed credentials'}), 401

    access = create_access_token(identity=user)
    refresh = create_refresh_token(identity=user)
    return jsonify({
        'access_token': access,
        'refresh_token': refresh,
        'user': user.to_dict()
    }), 200


@api_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def api_refresh():
    """Refresh access token using a refresh token."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    access = create_access_token(identity=user)
    return jsonify({'access_token': access}), 200


@api_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def api_me():
    """Return current user info from access token."""
    return jsonify({'user': jwt_current_user.to_dict()}), 200


@api_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def api_logout():
    """Stateless logout for JWT (client should discard tokens)."""
    return jsonify({'message': 'Logged out'}), 200

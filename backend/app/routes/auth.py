from typing import Tuple
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import db, User, Team
from app.utils.rate_limiter import limiter

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute") # strict rate limiting on login
def login() -> Tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid payload format'}), 400
        
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
        
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({'error': 'Email and password must be strings'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if user.is_banned:
        return jsonify({'error': 'Your account has been banned due to policy violations.'}), 403
        
    if user.team and user.team.is_banned:
        return jsonify({'error': 'Your team has been banned due to policy violations.'}), 403

    # Include role and team_id in the token payload if desired, but we can also just rely on user_id
    token = create_access_token(identity=str(user.id))
    return jsonify({
        'message': 'Login successful',
        'access_token': token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me() -> Tuple[Response, int]:
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    if user.is_banned or (user.team and user.team.is_banned):
        return jsonify({'error': 'Your account/team has been banned.'}), 403
        
    return jsonify({'user': user.to_dict()}), 200

import hashlib
import hmac
from typing import Tuple, Dict, Any, List
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Challenge, Submission, User, Team, TeamHint, ActivityLog
from app.utils.scoring import calculate_penalty
from app.utils.rate_limiter import limiter
from datetime import datetime
import os
import base64

challenges_bp = Blueprint('challenges', __name__, url_prefix='/api/challenges')

@challenges_bp.route('', methods=['GET'])
@jwt_required()
def get_open_challenges() -> Tuple[Response, int]:
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    
    if not user or user.is_banned or (user.team and user.team.is_banned):
        return jsonify({'error': 'Your account/team has been banned.'}), 403

    all_challenges = Challenge.query.all()
    solved_submissions = Submission.query.filter_by(team_id=user.team_id, is_correct=True).all()
    solved_challenge_ids = {s.challenge_id for s in solved_submissions}
    
    res = []
    for c in all_challenges:
        is_solved = c.id in solved_challenge_ids
        is_open = c.is_open()
        
        is_parent_solved = True
        if c.parent_id and c.parent_id not in solved_challenge_ids:
            is_parent_solved = False
            
        is_active = is_open and is_parent_solved
        
        c_dict = c.to_dict()
        c_dict['is_solved'] = is_solved
        c_dict['is_locked_by_parent'] = not is_parent_solved
        
        if is_active or is_solved:
            # Fully visible challenge
            if is_solved:
                correct_sub = next((s for s in solved_submissions if s.challenge_id == c.id), None)
                if correct_sub:
                    c_dict['points_earned'] = correct_sub.points_awarded
            
            c_dict['attempts'] = Submission.query.filter_by(team_id=user.team_id, challenge_id=c.id).count()
            
            # Populate unlocks_children (only those children that are visible/is_hidden=False)
            children = [ch.title for ch in all_challenges if ch.parent_id == c.id and not ch.is_hidden]
            c_dict['unlocks_children'] = children
            
            res.append(c_dict)
        else:
            # Closed or Locked challenge
            if c.is_hidden:
                # Hidden completely
                continue
            else:
                # Visible but locked/closed. Strip details.
                c_dict['description'] = None
                c_dict['attachment_filename'] = None
                c_dict['has_attachment'] = False
                c_dict['has_hint'] = False
                c_dict['hint_text'] = None
                
                children = [ch.title for ch in all_challenges if ch.parent_id == c.id and not ch.is_hidden]
                c_dict['unlocks_children'] = children
                
                res.append(c_dict)
        
    return jsonify({'challenges': res}), 200

@challenges_bp.route('/<int:challenge_id>/submit', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def submit_flag(challenge_id: int) -> Tuple[Response, int]:
    user_id = int(get_jwt_identity())
    
    user = User.query.filter_by(id=user_id).with_for_update().first()
    if not user or not user.team_id:
        return jsonify({'error': 'Forbidden. Banned or no team assigned.'}), 403
        
    team = Team.query.filter_by(id=user.team_id).with_for_update().first()
    if user.is_banned or team.is_banned:
        return jsonify({'error': 'Forbidden. Banned or no team assigned.'}), 403
    
    team = user.team
    challenge = db.session.get(Challenge, challenge_id, with_for_update=True)

    if not challenge:
        return jsonify({'error': 'Challenge not found'}), 404

    # Check parent solve dependency
    if challenge.parent_id:
        parent_solved = Submission.query.filter_by(team_id=team.id, challenge_id=challenge.parent_id, is_correct=True).first()
        if not parent_solved:
            return jsonify({'error': 'You must solve the parent challenge first.'}), 403

    if not challenge.is_open():
        return jsonify({'error': 'Challenge is not active in this time window.'}), 403

    already_solved = Submission.query.filter_by(team_id=team.id, challenge_id=challenge.id, is_correct=True).first()
    if already_solved:
        return jsonify({'error': 'Your team has already solved this challenge!'}), 400

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid payload format'}), 400
        
    submitted_flag = data.get('flag', '')
    if not isinstance(submitted_flag, str):
        return jsonify({'error': 'Invalid flag format. Must be a string.'}), 400

    submitted_hash = hashlib.sha256(submitted_flag.encode()).hexdigest()
    is_correct = hmac.compare_digest(submitted_hash, challenge.flag_hash)

    submission = Submission(
        team_id=team.id,
        user_id=user.id,
        challenge_id=challenge.id,
        is_correct=is_correct
    )
    
    if is_correct:
        solve_order = Submission.query.filter_by(challenge_id=challenge.id, is_correct=True).count() + 1
        calculated_points = challenge.max_points - ((solve_order - 1) * challenge.step_value)
        points_awarded = max(challenge.min_points, calculated_points)
        
        submission.points_awarded = points_awarded
        submission.solve_order = solve_order
        team.score += points_awarded
        user.score += points_awarded
        msg = f'Correct! Awarded {points_awarded} points (Solve #{solve_order}).'
    else:
        team.wrong_attempts += 1
        challenge_attempts = Submission.query.filter_by(team_id=team.id, challenge_id=challenge.id, is_correct=False).count() + 1
        penalty = calculate_penalty(challenge_attempts, penalty_value=challenge.penalty_value)
        submission.penalty_deducted = penalty
        team.score -= penalty
        user.score -= penalty
        
        if team.wrong_attempts > 50:
            team.is_banned = True
            msg = 'Incorrect flag. Penalty applied. EXCEEDED 50 ATTEMPTS: TEAM BANNED.'
        else:
            msg = f'Incorrect flag. Penalty deducted: {penalty} points.'

    activity = ActivityLog(
        team_id=team.id,
        user_id=user.id,
        action_type='submission',
        description=f'Submitted flag for challenge {challenge.id}. Correct: {is_correct}'
    )
    db.session.add(activity)
    
    if team.is_banned and team.wrong_attempts == 51:
        ban_log = ActivityLog(
            team_id=team.id,
            user_id=user.id,
            action_type='auto_ban',
            description='Team auto-banned after exceeding 50 wrong attempts.'
        )
        db.session.add(ban_log)

    db.session.add(submission)
    db.session.commit()

    if team.is_banned:
        return jsonify({'error': msg}), 403

    if is_correct:
        return jsonify({'message': msg, 'is_correct': True}), 200
    else:
        return jsonify({'error': msg, 'is_correct': False}), 400

@challenges_bp.route('/<int:challenge_id>', methods=['GET'])
@jwt_required()
def get_challenge(challenge_id: int) -> Tuple[Response, int]:
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    
    if not user or user.is_banned or not user.team or user.team.is_banned:
        return jsonify({'error': 'Forbidden. Banned or no team assigned.'}), 403

    challenge = db.get_or_404(Challenge, challenge_id)
    
    submissions = Submission.query.filter_by(team_id=user.team_id, challenge_id=challenge.id).all()
    is_solved = any(s.is_correct for s in submissions)
    
    is_open = challenge.is_open()
    is_parent_solved = True
    if challenge.parent_id:
        parent_solved_sub = Submission.query.filter_by(team_id=user.team_id, challenge_id=challenge.parent_id, is_correct=True).first()
        if not parent_solved_sub:
            is_parent_solved = False
            
    is_active = is_open and is_parent_solved
    
    if not (is_active or is_solved):
        if challenge.is_hidden:
            return jsonify({'error': 'Challenge not found or not active.'}), 403
        else:
            c_dict = challenge.to_dict()
            c_dict['is_solved'] = is_solved
            c_dict['is_locked_by_parent'] = not is_parent_solved
            c_dict['description'] = None
            c_dict['attachment_filename'] = None
            c_dict['has_attachment'] = False
            c_dict['has_hint'] = False
            c_dict['hint_text'] = None
            children = Challenge.query.filter_by(parent_id=challenge.id, is_hidden=False).all()
            c_dict['unlocks_children'] = [ch.title for ch in children]
            return jsonify({'challenge': c_dict}), 200

    c_dict = challenge.to_dict()
    c_dict['is_solved'] = is_solved
    c_dict['is_locked_by_parent'] = not is_parent_solved
    c_dict['attempts'] = len(submissions)
    
    if is_solved:
        correct_sub = next((s for s in submissions if s.is_correct), None)
        if correct_sub:
            c_dict['points_earned'] = correct_sub.points_awarded
    
    if challenge.hint_text:
        hint_unlocked = TeamHint.query.filter_by(team_id=user.team_id, challenge_id=challenge.id).first() is not None
        c_dict['hint_unlocked'] = hint_unlocked
        if not hint_unlocked:
            c_dict['hint_text'] = None
    else:
        c_dict['hint_unlocked'] = False

    children = Challenge.query.filter_by(parent_id=challenge.id, is_hidden=False).all()
    c_dict['unlocks_children'] = [ch.title for ch in children]

    return jsonify({'challenge': c_dict}), 200


@challenges_bp.route('/<int:challenge_id>/hint', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def unlock_hint(challenge_id: int):
    user_id = int(get_jwt_identity())
    
    user = User.query.filter_by(id=user_id).with_for_update().first()
    if not user or not user.team_id:
        return jsonify({'error': 'Forbidden.'}), 403
        
    team = Team.query.filter_by(id=user.team_id).with_for_update().first()
    if user.is_banned or team.is_banned:
        return jsonify({'error': 'Forbidden.'}), 403

    challenge = db.get_or_404(Challenge, challenge_id)
    
    if challenge.parent_id:
        parent_solved = Submission.query.filter_by(team_id=team.id, challenge_id=challenge.parent_id, is_correct=True).first()
        if not parent_solved:
            return jsonify({'error': 'You must solve the parent challenge first.'}), 403

    if not challenge.is_open():
        return jsonify({'error': 'Challenge is closed.'}), 403
        
    if not challenge.hint_text:
        return jsonify({'error': 'No hint available for this challenge.'}), 400
        
    team = user.team
    
    is_solved = Submission.query.filter_by(team_id=team.id, challenge_id=challenge.id, is_correct=True).first()
    if is_solved:
        return jsonify({'error': 'Challenge is already solved. Hints are disabled.'}), 400
        
    already_unlocked = TeamHint.query.filter_by(team_id=team.id, challenge_id=challenge.id).first()
    if already_unlocked:
        return jsonify({'message': 'Hint already unlocked.', 'hint_text': challenge.hint_text}), 200
        
    team.score -= challenge.hint_penalty
    user.score -= challenge.hint_penalty
    
    team_hint = TeamHint(team_id=team.id, challenge_id=challenge.id)
    
    activity = ActivityLog(
        team_id=team.id,
        user_id=user.id,
        action_type='hint_reveal',
        description=f'Unlocked hint for challenge {challenge.id} (-{challenge.hint_penalty} pts)'
    )
    
    db.session.add(team_hint)
    db.session.add(activity)
    db.session.commit()
    
    return jsonify({'message': f'Hint unlocked. {challenge.hint_penalty} points deducted.', 'hint_text': challenge.hint_text}), 200

@challenges_bp.route('/<int:challenge_id>/attachment', methods=['GET'])
@jwt_required()
@limiter.limit("10 per minute")
def download_attachment(challenge_id: int):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    
    if not user or user.is_banned or not user.team or user.team.is_banned:
        return jsonify({'error': 'Forbidden.'}), 403

    challenge = db.get_or_404(Challenge, challenge_id)
    if not challenge.attachment_path or not os.path.exists(challenge.attachment_path):
        return jsonify({'error': 'Attachment not found.'}), 404
        
    if challenge.parent_id:
        parent_solved = Submission.query.filter_by(team_id=user.team_id, challenge_id=challenge.parent_id, is_correct=True).first()
        if not parent_solved:
            return jsonify({'error': 'You must solve the parent challenge first.'}), 403

    submissions = Submission.query.filter_by(team_id=user.team_id, challenge_id=challenge.id).all()
    is_solved = any(s.is_correct for s in submissions)
    
    if is_solved:
        return jsonify({'error': 'Challenge already solved. Downloads disabled.'}), 403
        
    if not challenge.is_open():
        return jsonify({'error': 'Challenge is closed.'}), 403
        
    try:
        with open(challenge.attachment_path, 'rb') as f:
            file_bytes = f.read()
        b64_data = base64.b64encode(file_bytes).decode('utf-8')
        return jsonify({
            'filename': challenge.attachment_filename,
            'data': b64_data
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error reading file.'}), 500

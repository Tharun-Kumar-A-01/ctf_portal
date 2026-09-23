from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Team, Submission, db

team_bp = Blueprint('team', __name__, url_prefix='/api/team')

@team_bp.route('/me', methods=['GET'])
@jwt_required()
def get_my_team():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    
    if not user or not user.team:
        return jsonify({'error': 'No team assigned.'}), 404

    team = user.team
    t_dict = team.to_dict()
    
    # Calculate rank stably
    all_teams = Team.query.order_by(Team.score.desc(), Team.id.asc()).all()
    rank = next((i + 1 for i, t in enumerate(all_teams) if t.id == team.id), 0)
    t_dict['rank'] = rank

    from app.models import TeamHint, ActivityLog
    
    solved_submissions = Submission.query.filter_by(team_id=team.id, is_correct=True).order_by(Submission.timestamp.asc()).all()
    wrong_submissions = Submission.query.filter_by(team_id=team.id, is_correct=False).order_by(Submission.timestamp.asc()).all()
    team_hints = TeamHint.query.filter_by(team_id=team.id).all()
    
    total_earned = sum(s.points_awarded for s in solved_submissions)
    total_deducted_submissions = sum(s.penalty_deducted for s in wrong_submissions)
    total_deducted_hints = sum(th.challenge.hint_penalty for th in team_hints if th.challenge)
    
    t_dict['total_earned'] = total_earned
    t_dict['total_deducted'] = total_deducted_submissions + total_deducted_hints
    
    t_dict['solved_challenges'] = []
    for s in solved_submissions:
        t_dict['solved_challenges'].append({
            'challenge_id': s.challenge_id,
            'challenge_title': s.challenge.title if s.challenge else 'Unknown',
            'points_awarded': s.points_awarded,
            'solve_order': s.solve_order,
            'timestamp': s.timestamp.isoformat() if s.timestamp else None
        })
        
    t_dict['wrong_submissions'] = []
    for s in wrong_submissions:
        t_dict['wrong_submissions'].append({
            'challenge_id': s.challenge_id,
            'challenge_title': s.challenge.title if s.challenge else 'Unknown',
            'penalty_deducted': s.penalty_deducted,
            'timestamp': s.timestamp.isoformat() if s.timestamp else None
        })
        
    t_dict['hint_reveals'] = []
    for th in team_hints:
        t_dict['hint_reveals'].append({
            'challenge_id': th.challenge_id,
            'challenge_title': th.challenge.title if th.challenge else 'Unknown',
            'penalty_deducted': th.challenge.hint_penalty if th.challenge else 0.0,
            'timestamp': th.timestamp.isoformat() if th.timestamp else None
        })

    t_dict['members'] = []
    for member in team.users:
        t_dict['members'].append({
            'id': member.id,
            'username': member.username,
            'role': member.role,
            'is_team_leader': member.is_team_leader,
            'is_banned': member.is_banned,
            'score': member.score
        })
        
    return jsonify({'team': t_dict}), 200

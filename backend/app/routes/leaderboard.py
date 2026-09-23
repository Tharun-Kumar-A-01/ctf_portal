from flask import Blueprint, jsonify
from app.models import Team
from app.utils.rate_limiter import limiter

leaderboard_bp = Blueprint('leaderboard', __name__, url_prefix='/api/leaderboard')

@leaderboard_bp.route('', methods=['GET'])
@limiter.limit("3 per second")
@limiter.limit("180 per minute")
def get_global_leaderboard():
    # Rank all non-banned teams by score descending, then by id ascending (stable tie-breaker)
    teams = Team.query.filter_by(is_banned=False).order_by(Team.score.desc(), Team.id.asc()).all()
    
    rankings = []
    for rank, team in enumerate(teams, start=1):
        rankings.append({
            'rank': rank,
            'team_id': team.id,
            'team_name': team.name,
            'score': team.score
        })
        
    import json
    from app.e2e import redis_client
    
    timer_data = redis_client.get('ctf:global_timer')
    timer = json.loads(timer_data) if timer_data else None

    return jsonify({
        'rankings': rankings,
        'count': len(rankings),
        'timer': timer
    }), 200

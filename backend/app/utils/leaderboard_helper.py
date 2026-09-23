from sqlalchemy import func, desc
from app.models import db, Score, User

def get_leaderboard(category=None, limit=100, page=1):
    """
    Computes global or category-specific leaderboard rankings using SQL window functions.
    Handles tied scores using DENSE_RANK() or RANK().
    """
    offset = (page - 1) * limit
    
    # Subquery or direct aggregate query for highest score per user per category
    if category:
        # Rank users by total points in category
        subquery = (
            db.session.query(
                Score.user_id,
                func.sum(Score.points).label('total_points'),
                func.count(Score.id).label('submissions_count'),
                func.max(Score.updated_at).label('last_submission'),
                func.rank().over(
                    order_by=[desc(func.sum(Score.points)), func.max(Score.updated_at)]
                ).label('rank')
            )
            .filter(Score.category == category)
            .group_by(Score.user_id)
            .subquery()
        )
    else:
        # Global overall leaderboard
        subquery = (
            db.session.query(
                Score.user_id,
                func.sum(Score.points).label('total_points'),
                func.count(Score.id).label('submissions_count'),
                func.max(Score.updated_at).label('last_submission'),
                func.rank().over(
                    order_by=[desc(func.sum(Score.points)), func.max(Score.updated_at)]
                ).label('rank')
            )
            .group_by(Score.user_id)
            .subquery()
        )

    # Join with User table to fetch usernames
    query = (
        db.session.query(
            subquery.c.rank,
            subquery.c.user_id,
            User.username,
            subquery.c.total_points,
            subquery.c.submissions_count,
            subquery.c.last_submission
        )
        .join(User, User.id == subquery.c.user_id)
        .order_by(subquery.c.rank)
        .limit(limit)
        .offset(offset)
    )

    results = query.all()
    
    leaderboard_data = []
    for row in results:
        leaderboard_data.append({
            'rank': row.rank,
            'user_id': row.user_id,
            'username': row.username,
            'total_points': float(row.total_points or 0),
            'submissions_count': row.submissions_count,
            'last_submission': row.last_submission.isoformat() if row.last_submission else None
        })

    return leaderboard_data

def get_user_rank(user_id, category=None):
    """
    Finds a specific user's current rank and total score on the leaderboard.
    """
    board = get_leaderboard(category=category, limit=10000)
    for entry in board:
        if entry['user_id'] == user_id:
            return entry
    return None

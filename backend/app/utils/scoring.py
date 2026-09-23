from app.models import db, Submission, Team

def calculate_penalty(team_wrong_attempts, penalty_value=10.0):
    """
    Calculates penalty based on the configured challenge penalty value.
    Penalty = team_wrong_attempts * penalty_value
    """
    if team_wrong_attempts <= 2:
        return 0.0
    
    return float((team_wrong_attempts - 2) * penalty_value)

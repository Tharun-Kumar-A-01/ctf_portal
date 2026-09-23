from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    score = db.Column(db.Float, default=0.0)
    wrong_attempts = db.Column(db.Integer, default=0)
    is_banned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    users = db.relationship('User', backref='team', lazy=True)
    submissions = db.relationship('Submission', backref='team', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'score': self.score,
            'wrong_attempts': self.wrong_attempts,
            'is_banned': self.is_banned,
            'member_count': len(self.users),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user') # 'admin' or 'user'
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    score = db.Column(db.Float, default=0.0)
    is_team_leader = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    submissions = db.relationship('Submission', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'score': self.score,
            'team_id': self.team_id,
            'team_name': self.team.name if self.team else None,
            'is_team_leader': self.is_team_leader,
            'is_banned': self.is_banned,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Challenge(db.Model):
    __tablename__ = 'challenges'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    flag_hash = db.Column(db.String(255), nullable=False) # store hashed flag for security
    max_points = db.Column(db.Float, default=1000.0)
    min_points = db.Column(db.Float, default=300.0)
    step_value = db.Column(db.Float, default=100.0)
    penalty_value = db.Column(db.Float, default=10.0)
    status_override = db.Column(db.String(20), default='AUTO') # 'AUTO', 'OPEN', 'CLOSED'
    open_time = db.Column(db.DateTime, nullable=False)
    close_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_hidden = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=True)
    
    # Attachments & Hints
    attachment_filename = db.Column(db.String(255), nullable=True)
    attachment_path = db.Column(db.String(255), nullable=True)
    hint_text = db.Column(db.Text, nullable=True)
    hint_penalty = db.Column(db.Float, default=0.0)
    
    submissions = db.relationship('Submission', backref='challenge', lazy=True)
    team_hints = db.relationship('TeamHint', backref='challenge', lazy=True)
    parent = db.relationship('Challenge', remote_side=[id], backref='children', lazy=True)

    def is_open(self):
        if self.status_override == 'OPEN':
            return True
        if self.status_override == 'CLOSED':
            return False
            
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return self.open_time <= now <= self.close_time

    def to_dict(self):
        # Calculate current dynamic points
        solves_count = Submission.query.filter_by(challenge_id=self.id, is_correct=True).count()
        current_points = max(self.min_points, self.max_points - (solves_count * self.step_value))

        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'max_points': self.max_points,
            'min_points': self.min_points,
            'step_value': self.step_value,
            'penalty_value': self.penalty_value,
            'solves': solves_count,
            'points': current_points,
            'status_override': self.status_override,
            'open_time': self.open_time.isoformat() if self.open_time else None,
            'close_time': self.close_time.isoformat() if self.close_time else None,
            'is_open': self.is_open(),
            'has_attachment': bool(self.attachment_path),
            'attachment_filename': self.attachment_filename,
            'has_hint': bool(self.hint_text),
            'hint_penalty': self.hint_penalty,
            'is_hidden': self.is_hidden,
            'parent_id': self.parent_id
        }

class TeamHint(db.Model):
    __tablename__ = 'team_hints'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action_type = db.Column(db.String(50), nullable=False) # 'submission', 'hint_reveal', 'auto_ban'
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='activities', lazy=True)
    team = db.relationship('Team', backref='activities', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'team_name': self.team.name if self.team else None,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'action_type': self.action_type,
            'description': self.description,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class Submission(db.Model):
    __tablename__ = 'submissions'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    points_awarded = db.Column(db.Float, default=0.0)
    penalty_deducted = db.Column(db.Float, default=0.0)
    solve_order = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'user_id': self.user_id,
            'challenge_id': self.challenge_id,
            'is_correct': self.is_correct,
            'points_awarded': self.points_awarded,
            'penalty_deducted': self.penalty_deducted,
            'solve_order': self.solve_order,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class DataImport(db.Model):
    __tablename__ = 'data_imports'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    row_count = db.Column(db.Integer, default=0)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(30), default='completed')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'row_count': self.row_count,
            'uploaded_by': self.uploaded_by,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

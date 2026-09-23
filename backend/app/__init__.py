from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.middleware.proxy_fix import ProxyFix
import os

from app.config import Config
from app.models import db, User
from app.security import init_encryption
from app.utils.rate_limiter import limiter

jwt = JWTManager()

def init_db_safely(app):
    """Safely initializes the database tables and admin user, ensuring only one worker runs this via Valkey lock."""
    from app.utils.traffic import redis_client
    with app.app_context():
        if redis_client:
            # Try to acquire lock, expiring in 60s max to prevent deadlocks
            lock_acquired = redis_client.set("ctf:db_init_lock", "locked", nx=True, ex=60)
            if not lock_acquired:
                # Another worker is already initializing the database.
                return
                
        try:
            print("[*] Performing startup database initialization...")
            db.create_all()
            if not User.query.filter_by(role='admin').first():
                admin_user = os.environ.get('ADMIN_USERNAME', 'admin')
                admin_email = os.environ.get('ADMIN_EMAIL', 'admin@ctf.local')
                admin_pass = os.environ.get('ADMIN_PASSWORD')
                if admin_pass:
                    admin = User(username=admin_user, email=admin_email, role='admin')
                    admin.set_password(admin_pass)
                    db.session.add(admin)
                    db.session.commit()
                    print(f"[*] Admin user '{admin_user}' auto-created during boot.")
        except Exception as e:
            print(f"[SECURITY] DB Initialization failed during startup: {e}")
        finally:
            if redis_client:
                # We do not strictly need to delete the lock immediately, but it's cleaner
                redis_client.delete("ctf:db_init_lock")

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Trust Nginx proxy headers
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Initialize encryption key for database fields
    init_encryption(app.config['FERNET_KEY'])

    # Initialize Flask extensions
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    from flask import request
    @limiter.request_filter
    def exempt_ws():
        if request.path.startswith('/api/admin/traffic/stream'):
            return True
        return False

    # Initialize flask-sock
    from flask_sock import Sock
    sock = Sock(app)
    app.sock = sock

    from app.utils.traffic import init_traffic_monitor
    init_traffic_monitor(app)

    from app.e2e import e2e_bp, e2e_before_request, e2e_after_request

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.challenges import challenges_bp
    from app.routes.leaderboard import leaderboard_bp
    from app.routes.team import team_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(challenges_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(e2e_bp)
    
    from app.routes.admin import register_ws
    register_ws(app)
    
    # Register E2E middleware globally
    app.before_request(e2e_before_request)
    app.after_request(e2e_after_request)

    # Error handling to prevent leakage
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error occurred.'}), 500
        
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify(error="Rate limit exceeded. Please try again later."), 429

    # Safely initialize the database on startup
    init_db_safely(app)

    return app

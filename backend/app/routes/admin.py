from flask import Blueprint, request, jsonify, current_app
from app.models import db, User, Team, Challenge, Submission
from app.utils.decorators import admin_required
from app.utils.parser_helper import parse_csv_stream
from dateutil import parser
import hmac
import hashlib
from datetime import timezone

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/users', methods=['GET'])
@admin_required()
def get_users():
    users = User.query.all()
    teams = Team.query.all()
    return jsonify({
        'users': [u.to_dict() for u in users],
        'teams': [t.to_dict() for t in teams]
    }), 200

@admin_bp.route('/users', methods=['POST'])
@admin_required()
def create_user():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict): return jsonify({'error': 'Invalid payload format'}), 400
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    team_name = data.get('team_name')
    role = data.get('role', 'user')

    if not username or not email or not password or not team_name:
        return jsonify({'error': 'Username, email, password, and team_name are required'}), 400
        
    if not isinstance(username, str) or not isinstance(email, str) or not isinstance(password, str) or not isinstance(team_name, str):
        return jsonify({'error': 'Fields must be strings'}), 400
        
    if role not in ['admin', 'user']:
        return jsonify({'error': 'Role must be either admin or user'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    team = Team.query.filter_by(name=team_name).first()
    if not team:
        team = Team(name=team_name)
        db.session.add(team)
        db.session.flush() # get team.id

    user = User(username=username, email=email, role=role, team_id=team.id)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201

@admin_bp.route('/users/import-csv', methods=['POST'])
@admin_required()
def import_users_csv():
    data = request.get_json(silent=True)
    if data and 'file_content' in data:
        if not isinstance(data['file_content'], str):
            return jsonify({'error': 'file_content must be a string'}), 400
        from io import StringIO
        stream = StringIO(data['file_content'])
    else:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        if request.content_length and request.content_length > 5 * 1024 * 1024:
            return jsonify({'error': 'File too large (max 5MB)'}), 413
        
        file = request.files['file']
        stream = file.stream
        
    parsed = parse_csv_stream(stream)
    
    created_users = []
    for row in parsed['rows']:
        username = row.get('username')
        email = row.get('email')
        password = row.get('password')
        team_name = row.get('team_name')
        team_leader_name = row.get('team_leader_name')
        
        if not username or not password or not email or not team_name:
            continue
            
        if User.query.filter_by(username=username).first():
            continue
            
        team = Team.query.filter_by(name=team_name).first()
        if not team:
            team = Team(name=team_name)
            db.session.add(team)
            db.session.flush()
            
        is_leader = (username == team_leader_name) if team_leader_name else False
        user = User(username=username, email=email, role='user', team_id=team.id, is_team_leader=is_leader)
        user.set_password(password)
        db.session.add(user)
        created_users.append(username)
        
    db.session.commit()
    return jsonify({'message': f'Successfully imported {len(created_users)} users', 'users': created_users}), 201

@admin_bp.route('/challenges', methods=['GET'])
@admin_required()
def get_challenges():
    challenges = Challenge.query.all()
    # Admin gets to see the flags (but they are stored as hash, maybe we should just not return them)
    # The requirement says "admin adds challenge with actual string to check". So we hash it.
    return jsonify({'challenges': [c.to_dict() for c in challenges]}), 200

@admin_bp.route('/challenges', methods=['POST'])
@admin_required()
def create_challenge():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict): return jsonify({'error': 'Invalid payload format'}), 400
    title = data.get('title')
    description = data.get('description')
    flag = data.get('flag')
    open_time_str = data.get('open_time')
    close_time_str = data.get('close_time')

    if not title or not flag or not open_time_str or not close_time_str:
        return jsonify({'error': 'Title, flag, open_time, and close_time are required'}), 400
        
    if not isinstance(title, str) or not isinstance(flag, str) or not isinstance(open_time_str, str) or not isinstance(close_time_str, str):
        return jsonify({'error': 'Fields must be strings'}), 400

    try:
        dt_open = parser.parse(open_time_str)
        dt_close = parser.parse(close_time_str)
        
        # Ensure they are UTC naive datetimes for SQLAlchemy
        if dt_open.tzinfo:
            open_time = dt_open.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            open_time = dt_open
            
        if dt_close.tzinfo:
            close_time = dt_close.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            close_time = dt_close
            
    except Exception:
        return jsonify({'error': 'Invalid date format'}), 400

    # Store hashed flag for security
    flag_hash = hashlib.sha256(flag.encode()).hexdigest()

    status_override = data.get('status_override', 'AUTO')
    if not isinstance(status_override, str):
        return jsonify({'error': 'status_override must be a string'}), 400
        
    try:
        max_points = float(data.get('max_points', 1000.0))
        min_points = float(data.get('min_points', 300.0))
        step_value = float(data.get('step_value', 100.0))
        penalty_value = float(data.get('penalty_value', 10.0))
        hint_penalty = float(data.get('hint_penalty', 0.0))
    except (ValueError, TypeError):
        return jsonify({'error': 'Points must be numeric'}), 400

    is_hidden = bool(data.get('is_hidden', False))
    parent_id = data.get('parent_id')
    if parent_id is not None:
        try:
            parent_id = int(parent_id)
        except ValueError:
            return jsonify({'error': 'parent_id must be an integer'}), 400

    challenge = Challenge(
        title=title,
        description=description,
        flag_hash=flag_hash,
        status_override=status_override,
        open_time=open_time,
        close_time=close_time,
        max_points=max_points,
        min_points=min_points,
        step_value=step_value,
        penalty_value=penalty_value,
        hint_text=data.get('hint_text', ''),
        hint_penalty=hint_penalty,
        is_hidden=is_hidden,
        parent_id=parent_id
    )
    db.session.add(challenge)
    db.session.commit()

    return jsonify({'message': 'Challenge created', 'challenge': challenge.to_dict()}), 201

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required()
def edit_user(user_id):
    user = db.get_or_404(User, user_id)
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict): return jsonify({'error': 'Invalid payload format'}), 400
    
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    if 'role' in data:
        user.role = data['role']
    if 'is_banned' in data:
        user.is_banned = data['is_banned']
    if 'password' in data and data['password'].strip() != '':
        user.set_password(data['password'])
    if 'is_team_leader' in data:
        new_is_leader = bool(data['is_team_leader'])
        if new_is_leader and user.team_id:
            other_leaders = User.query.filter_by(team_id=user.team_id, is_team_leader=True).all()
            for leader in other_leaders:
                leader.is_team_leader = False
        user.is_team_leader = new_is_leader
        
    db.session.commit()
    return jsonify({'message': 'User updated successfully', 'user': user.to_dict()}), 200

@admin_bp.route('/challenges/<int:challenge_id>', methods=['PUT'])
@admin_required()
def edit_challenge(challenge_id):
    challenge = db.get_or_404(Challenge, challenge_id)
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict): return jsonify({'error': 'Invalid payload format'}), 400
    
    if 'title' in data:
        if not isinstance(data['title'], str): return jsonify({'error': 'title must be string'}), 400
        challenge.title = data['title']
    if 'description' in data:
        if not isinstance(data['description'], str): return jsonify({'error': 'description must be string'}), 400
        challenge.description = data['description']
        
    try:
        if 'max_points' in data: challenge.max_points = float(data['max_points'])
        if 'min_points' in data: challenge.min_points = float(data['min_points'])
        if 'step_value' in data: challenge.step_value = float(data['step_value'])
        if 'penalty_value' in data: challenge.penalty_value = float(data['penalty_value'])
        if 'hint_penalty' in data: challenge.hint_penalty = float(data['hint_penalty'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Points must be numeric'}), 400
        
    if 'hint_text' in data:
        challenge.hint_text = data['hint_text']
        
    if 'status_override' in data:
        if not isinstance(data['status_override'], str): return jsonify({'error': 'status_override must be string'}), 400
        challenge.status_override = data['status_override']
        
    if 'is_hidden' in data:
        challenge.is_hidden = bool(data['is_hidden'])
        
    if 'parent_id' in data:
        val = data['parent_id']
        if val is None:
            challenge.parent_id = None
        else:
            try:
                challenge.parent_id = int(val)
            except ValueError:
                return jsonify({'error': 'parent_id must be an integer or null'}), 400
                
    if 'open_time' in data and 'close_time' in data:
        try:
            dt_open = parser.parse(data['open_time'])
            dt_close = parser.parse(data['close_time'])
            if dt_open.tzinfo:
                challenge.open_time = dt_open.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                challenge.open_time = dt_open
            
            if dt_close.tzinfo:
                challenge.close_time = dt_close.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                challenge.close_time = dt_close
        except Exception:
            return jsonify({'error': 'Invalid date format'}), 400
            
    if 'flag' in data and data['flag']:
        challenge.flag_hash = hashlib.sha256(data['flag'].encode()).hexdigest()
        
    db.session.commit()
    return jsonify({'message': 'Challenge updated successfully', 'challenge': challenge.to_dict()}), 200

@admin_bp.route('/challenges/<int:challenge_id>/submissions', methods=['GET'])
@admin_required()
def get_challenge_submissions(challenge_id):
    submissions = Submission.query.filter_by(challenge_id=challenge_id).order_by(Submission.timestamp.desc()).all()
    res = []
    for s in submissions:
        res.append({
            'team_name': s.team.name if s.team else 'Unknown',
            'user_email': s.user.email if s.user else 'Unknown',
            'is_correct': s.is_correct,
            'timestamp': s.timestamp.isoformat() if s.timestamp else None
        })
    return jsonify({'submissions': res}), 200

@admin_bp.route('/challenges/<int:challenge_id>', methods=['DELETE'])
@admin_required()
def delete_challenge(challenge_id):
    challenge = db.get_or_404(Challenge, challenge_id)
    
    import os
    if challenge.attachment_path and os.path.exists(challenge.attachment_path):
        try:
            os.remove(challenge.attachment_path)
        except Exception as e:
            print(f"Failed to remove attachment file: {e}")
            
    # delete associated submissions first to avoid FK constraint fails
    Submission.query.filter_by(challenge_id=challenge_id).delete()
    db.session.delete(challenge)
    db.session.commit()
    return jsonify({'message': 'Challenge deleted successfully'}), 200

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required()
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    team_id = user.team_id
    # delete submissions associated with this user
    Submission.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    
    # Auto-delete team if empty
    if team_id:
        team = db.session.get(Team, team_id)
        if team and not team.users:
            # delete team hints and submissions
            TeamHint.query.filter_by(team_id=team_id).delete()
            Submission.query.filter_by(team_id=team_id).delete()
            db.session.delete(team)
            db.session.commit()
            
    return jsonify({'message': 'User deleted successfully'}), 200

@admin_bp.route('/teams/<int:team_id>', methods=['DELETE'])
@admin_required()
def delete_team(team_id):
    team = db.get_or_404(Team, team_id)
    
    # delete all users in team
    for user in team.users:
        Submission.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        
    TeamHint.query.filter_by(team_id=team_id).delete()
    Submission.query.filter_by(team_id=team_id).delete()
    db.session.delete(team)
    db.session.commit()
    return jsonify({'message': 'Team deleted successfully'}), 200
@admin_bp.route('/teams/<int:team_id>', methods=['PUT'])
@admin_required()
def edit_team(team_id):
    team = db.get_or_404(Team, team_id)
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict): return jsonify({'error': 'Invalid payload format'}), 400
    
    if 'is_banned' in data:
        if not isinstance(data['is_banned'], bool):
            return jsonify({'error': 'is_banned must be boolean'}), 400
        team.is_banned = data['is_banned']
        # Optionally ban/unban all users in team to keep them in sync, 
        # though the backend endpoints (auth.py, challenges.py) already block if team.is_banned is True.
        
    db.session.commit()
    return jsonify({'message': 'Team updated successfully', 'team': team.to_dict()}), 200

from app.utils.traffic import redis_client
import json

@admin_bp.route('/traffic', methods=['GET'])
@admin_required()
def get_traffic():
    if not redis_client:
        return jsonify({'error': 'Traffic monitoring is offline (Valkey unavailable)'}), 503
        
    raw_logs = redis_client.lrange('ctf:traffic_logs', 0, 9999)
    logs = [json.loads(l) for l in raw_logs]
    
    return jsonify({'logs': logs}), 200

@admin_bp.route('/banned-ips', methods=['GET'])
@admin_required()
def get_banned_ips():
    if not redis_client:
        return jsonify({'error': 'Valkey unavailable'}), 503
    
    ips = redis_client.smembers('ctf:banned_ips')
    return jsonify({'banned_ips': [ip.decode() for ip in ips]}), 200

@admin_bp.route('/banned-ips', methods=['POST'])
@admin_required()
def add_banned_ip():
    if not redis_client:
        return jsonify({'error': 'Valkey unavailable'}), 503
        
    data = request.get_json(silent=True) or {}
    ip = data.get('ip')
    if not ip:
        return jsonify({'error': 'IP is required'}), 400
        
    redis_client.sadd('ctf:banned_ips', ip)
    redis_client.publish('ctf:traffic_events', json.dumps({
        "type": "ban",
        "ip": ip
    }))
    return jsonify({'message': f'IP {ip} banned successfully'}), 201

import time

@admin_bp.route('/banned-ips/<ip>', methods=['DELETE'])
@admin_required()
def unban_ip(ip):
    print("unban_ip start")
    from app.utils.traffic import redis_client
    print("imported redis_client")
    if not redis_client:
        return jsonify({'error': 'Valkey unavailable'}), 503
        
    redis_client.srem('ctf:banned_ips', ip)
    redis_client.delete(f'ctf:strikes:{ip}')
    import json
    redis_client.publish('ctf:traffic_events', json.dumps({
        "type": "unban",
        "ip": ip
    }))
    print("unban_ip end")
    return jsonify({"message": f"IP {ip} unbanned."})

# Initialize WebSocket on the blueprint
def register_ws(app):
    from app.e2e import aes_gcm_encrypt, get_session_key
    from flask_jwt_extended import decode_token
    import base64
    import json
    import time as _time

    # Maximum number of log entries to send in a single WebSocket batch frame.
    # Prevents a single massive frame from overwhelming the client.
    _MAX_BATCH_SIZE: int = 200
    # How often (in seconds) the WebSocket drains the batch queue.
    _FLUSH_INTERVAL: float = 1.0

    def _encrypt_and_send(ws, aes_key: bytes, payload_str: str) -> None:
        """Encrypts a JSON string with the session AES key and sends it."""
        if aes_key:
            iv, ciphertext, tag = aes_gcm_encrypt(aes_key, payload_str.encode('utf-8'))
            e2e_payload = f"{base64.b64encode(iv).decode()}.{base64.b64encode(ciphertext).decode()}.{base64.b64encode(tag).decode()}"
            ws.send(json.dumps({"e2e_payload": e2e_payload}))
        else:
            ws.send(payload_str)

    @app.sock.route('/api/admin/traffic/stream')
    def traffic_stream(ws):
        from flask import request
        session_id = request.cookies.get('session_id')
        from app.utils.traffic import redis_client as _rc
        aes_key = _rc.get(f"ctf:e2e:session:{session_id}") if session_id else None

        # Authenticate: expect the first message to contain the JWT
        token_msg = ws.receive(timeout=5)
        if not token_msg:
            ws.send(json.dumps({"error": "No token provided"}))
            ws.close()
            return

        try:
            token_data = json.loads(token_msg)

            # Handle E2E encrypted payload strictly if provided
            if 'e2e_payload' in token_data:
                if not aes_key:
                    raise ValueError("No E2E session key found")

                from app.e2e import aes_gcm_decrypt
                payload_parts = token_data['e2e_payload'].split('.')
                iv = base64.b64decode(payload_parts[0])
                ciphertext = base64.b64decode(payload_parts[1])
                tag = base64.b64decode(payload_parts[2])

                decrypted_bytes = aes_gcm_decrypt(aes_key, iv, ciphertext, tag)
                decrypted_json = json.loads(decrypted_bytes.decode('utf-8'))
                token = decrypted_json.get('token')
            else:
                token = token_data.get('token')

            if not token:
                raise ValueError("No token in payload")

            decoded = decode_token(token)
            user_id: str = str(decoded['sub'])

            # Verify admin role from DB
            from app.models import User
            user = db.session.get(User, user_id)
            if not user or user.role != 'admin':
                raise ValueError("Not admin")

        except Exception:
            ws.send(json.dumps({"error": "Unauthorized"}))
            ws.close()
            return

        from app.utils.traffic import redis_client

        # --- Send initial state ---
        raw_logs = redis_client.lrange('ctf:traffic_logs', 0, 9999)
        initial_logs = [json.loads(l) for l in raw_logs]
        banned_ips = [ip.decode() for ip in redis_client.smembers('ctf:banned_ips')]

        init_payload = json.dumps({
            "type": "init",
            "logs": initial_logs,
            "banned_ips": banned_ips
        })
        _encrypt_and_send(ws, aes_key, init_payload)

        # --- Subscribe to ban/unban events (rare, must be real-time) ---
        pubsub = redis_client.pubsub()
        pubsub.subscribe('ctf:traffic_events')

        last_flush: float = _time.monotonic()
        last_ping: float = _time.monotonic()

        while True:
            try:
                now: float = _time.monotonic()

                # 1) Check for ban/unban events (non-blocking)
                msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.0)
                while msg:
                    try:
                        event_str: str = msg['data'].decode('utf-8')
                        _encrypt_and_send(ws, aes_key, event_str)
                    except Exception:
                        pass
                    msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.0)

                # 2) Drain the batch queue at the flush interval
                if now - last_flush >= _FLUSH_INTERVAL:
                    last_flush = now

                    # Atomically pop all pending entries and clear the queue
                    pipe = redis_client.pipeline(transaction=True)
                    pipe.lrange('ctf:traffic_batch', 0, -1)
                    pipe.delete('ctf:traffic_batch')
                    results = pipe.execute()
                    raw_batch = results[0]

                    if raw_batch:
                        # Cap at 1000 most recent logs to save bandwidth during massive attacks
                        if len(raw_batch) > 1000:
                            raw_batch = raw_batch[-1000:]
                        batch_logs = [json.loads(entry) for entry in raw_batch]
                        batch_payload = json.dumps({
                            "type": "batch",
                            "logs": batch_logs
                        })
                        _encrypt_and_send(ws, aes_key, batch_payload)

                # 3) Sleep briefly to avoid busy-waiting
                _time.sleep(0.1)
                
                # 4) Send keepalive ping every 30 seconds
                if now - last_ping >= 30.0:
                    last_ping = now
                    ws.send('ping')

            except Exception:
                # Connection closed or other error — exit cleanly
                break

        pubsub.close()

import os
import uuid
from werkzeug.utils import secure_filename
from app.models import ActivityLog
import json
from app.e2e import redis_client

@admin_bp.route('/challenges/<int:challenge_id>/attachment', methods=['POST'])
@admin_required()
def upload_attachment(challenge_id):
    challenge = db.get_or_404(Challenge, challenge_id)
    data = request.get_json(silent=True) or {}
    
    filename = data.get('filename')
    base64_data = data.get('data')
    
    if not filename or not base64_data:
        return jsonify({'error': 'Filename and data required'}), 400
        
    upload_dir = os.path.join(current_app.instance_path, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    safe_name = secure_filename(filename)
    unique_name = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = os.path.join(upload_dir, unique_name)
    
    import base64
    try:
        file_bytes = base64.b64decode(base64_data)
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
    except Exception as e:
        return jsonify({'error': 'Invalid base64 data'}), 400
        
    challenge.attachment_filename = filename
    challenge.attachment_path = file_path
    db.session.commit()
    
    return jsonify({'message': 'Attachment uploaded successfully'})

@admin_bp.route('/timer', methods=['POST'])
@admin_required()
def set_timer():
    data = request.get_json(silent=True) or {}
    note = data.get('note', '')
    expires_at = data.get('expires_at')
    
    if not expires_at:
        return jsonify({'error': 'expires_at is required'}), 400
        
    try:
        parser.parse(expires_at)
    except Exception:
        return jsonify({'error': 'Invalid date format'}), 400

    if not redis_client:
        return jsonify({'error': 'Redis/Valkey is not connected'}), 503

    redis_client.set("ctf:global_timer", json.dumps({"note": note, "expires_at": expires_at}))
    return jsonify({'message': 'Timer set'})

@admin_bp.route('/timer', methods=['DELETE'])
@admin_required()
def clear_timer():
    if not redis_client:
        return jsonify({'error': 'Redis/Valkey is not connected'}), 503
    redis_client.delete("ctf:global_timer")
    return jsonify({'message': 'Timer cleared'})

@admin_bp.route('/activity', methods=['GET'])
@admin_required()
def get_activity():
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(200).all()
    return jsonify({'activities': [log.to_dict() for log in logs]})

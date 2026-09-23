import pytest
import hashlib
import base64
from app.models import db, Challenge, Team, User, ActivityLog, TeamHint
from datetime import datetime, timedelta, timezone

def test_fetch_challenges_unauthorized(client):
    res = client.get('/api/challenges')
    assert res.status_code == 401

def test_fetch_and_solve_challenges(client, app):
    """Mocks a challenge creation and attempts to solve it from a standard user."""
    # First, setup the challenge in DB
    with app.app_context():
        new_chal = Challenge(
            title="Test Crypto",
            description="Decrypt this.",
            flag_hash=hashlib.sha256("CTF{test_flag_123}".encode()).hexdigest(),
            max_points=1000,
            min_points=300,
            step_value=100,
            penalty_value=10,
            status_override='OPEN',
            open_time=datetime.now(timezone.utc) - timedelta(days=1),
            close_time=datetime.now(timezone.utc) + timedelta(days=1)
        )
        db.session.add(new_chal)
        db.session.commit()
        chal_id = new_chal.id

    with app.app_context():

        team = Team(name="Test Team")
        db.session.add(team)
        db.session.commit()
        
        user = User(username="testuser", email="test@test.com", role="user", team_id=team.id)
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    # Get standard user token
    res_login = client.post('/api/auth/login', json={"email": "test@test.com", "password": "testpass"})
    token = res_login.get_json()['access_token']
    
    # Assert challenge is listed
    list_res = client.get('/api/challenges', headers={"Authorization": f"Bearer {token}"})
    assert list_res.status_code == 200
    chals = list_res.get_json()['challenges']
    assert any(c['title'] == 'Test Crypto' for c in chals)
    
    # Try invalid flag
    solve_res = client.post(f'/api/challenges/{chal_id}/submit', 
                            json={"flag": "CTF{wrong_flag}"},
                            headers={"Authorization": f"Bearer {token}"})
    assert solve_res.status_code == 400
    assert not solve_res.get_json()['is_correct']
    
    # Try valid flag
    solve_res_correct = client.post(f'/api/challenges/{chal_id}/submit', 
                            json={"flag": "CTF{test_flag_123}"},
                            headers={"Authorization": f"Bearer {token}"})
                            
    assert solve_res_correct.status_code == 200
    assert solve_res_correct.get_json()['is_correct']



def test_hints_and_penalties(client, app):
    with app.app_context():
        new_chal = Challenge(
            title="Hinted", description="Find it.",
            flag_hash=hashlib.sha256(b"CTF{hint}").hexdigest(),
            max_points=1000, min_points=300, step_value=100, penalty_value=10,
            status_override='OPEN', hint_text="Here is a hint", hint_penalty=50.0,
            open_time=datetime.now(timezone.utc) - timedelta(days=1),
            close_time=datetime.now(timezone.utc) + timedelta(days=1)
        )
        db.session.add(new_chal)
        

        team = Team(name="Hint Team", score=100.0)
        db.session.add(team)
        db.session.commit()
        user = User(username="hintuser", email="hint@test.com", role="user", team_id=team.id, score=100.0)
        user.set_password("hintpass")
        db.session.add(user)
        db.session.commit()
        chal_id = new_chal.id
        team_id = team.id
        
    res_login = client.post('/api/auth/login', json={"email": "hint@test.com", "password": "hintpass"})
    token = res_login.get_json()['access_token']
    
    res = client.post(f'/api/challenges/{chal_id}/hint', headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    assert res.get_json()['hint_text'] == "Here is a hint"
    
    with app.app_context():

        t = db.session.get(Team, team_id)
        assert t.score == 50.0
        
    res2 = client.post(f'/api/challenges/{chal_id}/hint', headers={'Authorization': f'Bearer {token}'})
    assert res2.status_code == 200
    with app.app_context():

        t = db.session.get(Team, team_id)
        assert t.score == 50.0
        
    with app.app_context():
        logs = ActivityLog.query.filter_by(team_id=team_id).all()
        assert len(logs) == 1
        assert logs[0].action_type == 'hint_reveal'

def test_user_attachment_download(client, app):
    # Setup chal with file
    with app.app_context():
        chal = Challenge(
            title="UserFile", description="File",
            flag_hash=hashlib.sha256(b"CTF{file}").hexdigest(),
            max_points=100, min_points=30, step_value=10, penalty_value=1,
            status_override='OPEN',
            open_time=datetime.now(timezone.utc) - timedelta(days=1),
            close_time=datetime.now(timezone.utc) + timedelta(days=1)
        )
        db.session.add(chal)
        db.session.commit()
        chal_id = chal.id
        

        team = Team(name="UserFile Team")
        db.session.add(team)
        db.session.commit()
        user = User(username="ufileuser", email="ufile@test.com", role="user", team_id=team.id)
        user.set_password("filepass")
        db.session.add(user)
        db.session.commit()
        
    # Admin uploads it
    res_login = client.post('/api/auth/login', json={'email': 'admin@test.com', 'password': 'adminpass'})
    admin_token = res_login.get_json()['access_token']
    
    b64_data = base64.b64encode(b"Secret File Content").decode('utf-8')
    client.post(f'/api/admin/challenges/{chal_id}/attachment', 
                json={'filename': 'secret.txt', 'data': b64_data},
                headers={'Authorization': f'Bearer {admin_token}'})
                
    # User downloads it
    res_login = client.post('/api/auth/login', json={"email": "ufile@test.com", "password": "filepass"})
    user_token = res_login.get_json()['access_token']
    
    res_down = client.get(f'/api/challenges/{chal_id}/attachment', headers={'Authorization': f'Bearer {user_token}'})
    assert res_down.status_code == 200
    assert res_down.get_json()['filename'] == 'secret.txt'
    assert base64.b64decode(res_down.get_json()['data']) == b"Secret File Content"

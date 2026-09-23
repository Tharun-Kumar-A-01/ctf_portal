import pytest
from app.models import db, User, Challenge
from datetime import datetime, timedelta, timezone
import base64
import hashlib

def get_admin_token(client):
    res = client.post('/api/auth/login', json={"email": "admin@test.com", "password": "adminpass"})
    return res.get_json()['access_token']

def test_admin_traffic_access(client):
    """Ensure non-admins cannot access traffic metrics."""
    # Try unauthorized
    res = client.get('/api/admin/traffic')
    assert res.status_code == 401
    
    # Try with admin token
    token = get_admin_token(client)
    res_log = client.get('/api/admin/traffic', headers={'Authorization': f'Bearer {token}'})
    assert res_log.status_code == 200

def test_admin_timer(client, app):
    res_login = client.post('/api/auth/login', json={'email': 'admin@test.com', 'password': 'adminpass'})
    token = res_login.get_json()['access_token']
    
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    res = client.post('/api/admin/timer', json={'note': 'HACKING BEGINS', 'expires_at': expires_at}, headers={'Authorization': f'Bearer {token}'})
    assert res.status_code == 200
    
    res_lb = client.get('/api/leaderboard')
    assert 'timer' in res_lb.get_json()
    assert res_lb.get_json()['timer']['note'] == 'HACKING BEGINS'
    
    res_del = client.delete('/api/admin/timer', headers={'Authorization': f'Bearer {token}'})
    assert res_del.status_code == 200
    
    assert client.get('/api/leaderboard').get_json().get('timer') is None

def test_admin_attachment_upload(client, app):
    res_login = client.post('/api/auth/login', json={'email': 'admin@test.com', 'password': 'adminpass'})
    token = res_login.get_json()['access_token']
    
    with app.app_context():
        chal = Challenge(
            title="File", description="File",
            flag_hash=hashlib.sha256(b"CTF{file}").hexdigest(),
            max_points=100, min_points=30, step_value=10, penalty_value=1,
            status_override='OPEN',
            open_time=datetime.now(timezone.utc) - timedelta(days=1),
            close_time=datetime.now(timezone.utc) + timedelta(days=1)
        )
        db.session.add(chal)
        db.session.commit()
        chal_id = chal.id
        
    b64_data = base64.b64encode(b"Secret File Content").decode('utf-8')
    res_upload = client.post(f'/api/admin/challenges/{chal_id}/attachment', 
                             json={'filename': 'secret.txt', 'data': b64_data},
                             headers={'Authorization': f'Bearer {token}'})
    assert res_upload.status_code in [200, 503] # 503 if Valkey is missing during tests

def test_admin_banning_system(client, app):
    print("Getting token")
    token = get_admin_token(client)
    
    print("Adding banned IP")
    # Add a banned IP
    res = client.post('/api/admin/banned-ips', 
                      json={"ip": "192.168.1.100"},
                      headers={"Authorization": f"Bearer {token}"})
                      
    print("Asserting 201")
    assert res.status_code == 201
    
    # Verify it exists
    res_list = client.get('/api/admin/banned-ips', headers={"Authorization": f"Bearer {token}"})
    assert "192.168.1.100" in res_list.get_json()['banned_ips']
    
    # Delete the banned IP
    res_del = client.delete('/api/admin/banned-ips/192.168.1.100', headers={"Authorization": f"Bearer {token}"})
    assert res_del.status_code == 200
    
    # Verify gone
    res_list2 = client.get('/api/admin/banned-ips', headers={"Authorization": f"Bearer {token}"})
    assert "192.168.1.100" not in res_list2.get_json()['banned_ips']

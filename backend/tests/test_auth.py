import pytest
from app.models import db, User

def test_login_missing_credentials(client):
    """Test login fails when credentials are missing"""
    res = client.post('/api/auth/login', json={})
    assert res.status_code == 400
    assert 'Email and password are required' in res.get_json()['error']

def test_login_success(client):
    """Test admin login with correct credentials seeded from conftest"""
    res = client.post('/api/auth/login', json={
        "email": "admin@test.com",
        "password": "adminpass"
    })
    
    # Normally this might hit 429 if rate limiter trips, but conftest disabled it
    assert res.status_code == 200
    data = res.get_json()
    assert 'access_token' in data
    assert data['user']['email'] == 'admin@test.com'
    assert data['user']['role'] == 'admin'
    
def test_login_banned_user(client, app):
    """Test standard banned user rejection logic"""
    with app.app_context():
        banned_user = User(username="hacker", email="hacker@test.com")
        banned_user.set_password("pass123")
        banned_user.is_banned = True
        db.session.add(banned_user)
        db.session.commit()

    res = client.post('/api/auth/login', json={
        "email": "hacker@test.com",
        "password": "pass123"
    })
    
    assert res.status_code == 403
    assert 'banned' in res.get_json()['error'].lower()

def test_protected_routes(client):
    """Test JWT middleware validates tokens properly"""
    # Try accessing /me without token
    res = client.get('/api/auth/me')
    assert res.status_code == 401

    # Login to get token
    login_res = client.post('/api/auth/login', json={
        "email": "admin@test.com",
        "password": "adminpass"
    })
    token = login_res.get_json()['access_token']

    # Access /me with token
    res_auth = client.get('/api/auth/me', headers={"Authorization": f"Bearer {token}"})
    assert res_auth.status_code == 200
    assert res_auth.get_json()['user']['username'] == 'testadmin'

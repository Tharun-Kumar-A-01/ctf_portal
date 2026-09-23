import pytest
import os
from app import create_app
from app.models import db, User

from app.config import Config
from unittest.mock import patch

class TestConfig(Config):
    TESTING = True
    RATELIMIT_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

from unittest.mock import patch, MagicMock

class FakeRedis:
    def __init__(self):
        self.store = {}
        self.sets = {}
    def get(self, key):
        return self.store.get(key)
    def set(self, key, value, *args, **kwargs):
        self.store[key] = value
    def delete(self, key):
        self.store.pop(key, None)
    def smembers(self, key):
        return list(self.sets.get(key, set()))
    def sadd(self, key, member):
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].add(member.encode('utf-8') if isinstance(member, str) else member)
    def srem(self, key, member):
        if key in self.sets:
            m = member.encode('utf-8') if isinstance(member, str) else member
            self.sets[key].discard(m)
    def lrange(self, key, *args):
        return []
    def publish(self, channel, message):
        pass
    def setex(self, key, time, value):
        self.store[key] = value
    def pubsub(self):
        mock_pubsub = MagicMock()
        return mock_pubsub

@pytest.fixture(scope="session", autouse=True)
def mock_traffic():
    mock_redis = FakeRedis()
    
    with patch('app.utils.traffic.check_banned_ips', return_value=None), \
         patch('app.utils.traffic.log_traffic', side_effect=lambda r: r), \
         patch('app.utils.traffic.redis_client', mock_redis), \
         patch('app.routes.admin.redis_client', mock_redis), \
         patch('app.e2e.redis_client', mock_redis):
        yield

@pytest.fixture(scope="session")
def app():
    # Force test configuration
    app = create_app(TestConfig)

    # Note: SQLite works well for basic DB logic. 
    # For hardcore Postgres testing, this could point to a test postgres container.
    with app.app_context():
        db.create_all()
        # Seed an admin user for integrations
        admin = User(username='testadmin', email='admin@test.com', role='admin')
        admin.set_password('adminpass')
        db.session.add(admin)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

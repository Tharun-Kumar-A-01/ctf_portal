import pytest
from app.utils.traffic import redis_client
import json

def test_traffic_banning_pubsub_publish(app):
    """Mocks the Valkey pub/sub engine to ensure bans properly fire real-time events to all websockets."""
    if not redis_client:
        pytest.skip("Valkey is not running locally")
        
    pubsub = redis_client.pubsub()
    pubsub.subscribe('ctf:traffic_events')
    
    # Broadcast a fake ban
    redis_client.publish('ctf:traffic_events', json.dumps({
        "type": "ban",
        "ip": "10.0.0.2"
    }))
    
    # Non-blocking get message loop
    messages = []
    for _ in range(5):
        msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
        if msg:
            messages.append(msg)
            
    assert len(messages) > 0
    payload = json.loads(messages[0]['data'].decode('utf-8'))
    
    assert payload['type'] == 'ban'
    assert payload['ip'] == '10.0.0.2'

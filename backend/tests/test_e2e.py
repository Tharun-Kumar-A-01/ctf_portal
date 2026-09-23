import json
import base64
import os
from unittest.mock import patch, MagicMock
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

def test_handshake_creates_session(client):
    # Get the server's public key
    res = client.get('/api/e2e/public-key')
    assert res.status_code == 200
    pub_key_pem = res.json['public_key']
    
    # Load the public key to encrypt a mock AES key
    pub_key = serialization.load_pem_public_key(pub_key_pem.encode())
    
    mock_aes_key = os.urandom(32)
    encrypted_aes_key = pub_key.encrypt(
        mock_aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    payload = {
        "encrypted_aes_key": base64.b64encode(encrypted_aes_key).decode('utf-8')
    }
    
    mock_redis = MagicMock()
    with patch('app.e2e.redis_client', mock_redis):
        res = client.post('/api/e2e/handshake', json=payload)
        
        assert res.status_code == 200
        assert "Handshake successful" in res.json['message']
        
        # Verify HttpOnly cookie was set
        cookies = res.headers.getlist('Set-Cookie')
        session_cookie = next((c for c in cookies if 'session_id=' in c), None)
        assert session_cookie is not None
        assert 'HttpOnly' in session_cookie
        assert 'SameSite=Lax' in session_cookie
        
        # Verify Redis was updated with the session ID
        assert mock_redis.setex.call_count == 2

def test_session_key_retrieval_and_decryption(app):
    from app.e2e import get_session_key, aes_gcm_encrypt, aes_gcm_decrypt
    
    session_id = "test_session_id_456"
    aes_key = os.urandom(32)
    
    mock_redis = MagicMock()
    mock_redis.get.return_value = aes_key
    
    # Test getting session key via cookie
    with app.test_request_context(headers={'Cookie': f'session_id={session_id}'}), patch('app.e2e.redis_client', mock_redis):
        retrieved_key = get_session_key()
        assert retrieved_key == aes_key
        mock_redis.get.assert_called_once_with(f"ctf:e2e:session:{session_id}")
        
        # Test encryption/decryption with retrieved key
        payload = b'{"secret": "data"}'
        iv, ciphertext, tag = aes_gcm_encrypt(retrieved_key, payload)
        decrypted = aes_gcm_decrypt(retrieved_key, iv, ciphertext, tag)
        assert decrypted == payload


import json
import base64
import os
from flask import Blueprint, request, jsonify, g
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from flask_jwt_extended import decode_token
from app.utils.traffic import redis_client

# Dynamically resolve instance folder path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
KEY_FILE = os.environ.get('E2E_KEY_FILE', os.path.join(INSTANCE_DIR, "e2e_private_key.pem"))

# Auto-generate server key if missing (creates smooth dev experience)
if not os.path.exists(KEY_FILE):
    print(f"[*] E2E key not found, auto-generating Dev Key at {KEY_FILE}...")
    os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    temp_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(KEY_FILE, "wb") as f:
        f.write(temp_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

with open(KEY_FILE, "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

public_key = private_key.public_key()

public_key_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

e2e_bp = Blueprint('e2e', __name__, url_prefix='/api/e2e')

@e2e_bp.route('/public-key', methods=['GET'])
def get_public_key():
    return jsonify({"public_key": public_key_pem}), 200

def get_client_ip():
    ip = request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    return ip

@e2e_bp.route('/handshake', methods=['POST'])
def handshake():
    if not redis_client:
        return jsonify({"error": "Valkey unavailable"}), 503
        
    data = request.get_json(silent=True) or {}
    encrypted_aes_base64 = data.get('encrypted_aes_key')
    
    if not encrypted_aes_base64:
        return jsonify({"error": "Missing encrypted_aes_key"}), 400
        
    try:
        encrypted_aes_bytes = base64.b64decode(encrypted_aes_base64)
        aes_key = private_key.decrypt(
            encrypted_aes_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        session_id = os.urandom(32).hex()
        
        # Store key and ip mapped to session id
        redis_client.setex(f"ctf:e2e:session:{session_id}", 3600 * 24, aes_key)
        ip = get_client_ip()
        redis_client.setex(f"ctf:e2e:session:{session_id}:ip", 3600 * 24, ip)
        
        resp = jsonify({"message": "Handshake successful"})
        is_secure = request.is_secure or request.headers.get('X-Forwarded-Proto', 'http') == 'https'
        resp.set_cookie('session_id', session_id, httponly=True, secure=is_secure, samesite='Lax', max_age=3600*24)
        return resp, 200
        
    except Exception as e:
        return jsonify({"error": "Decryption failed"}), 400

def get_session_key():
    if not redis_client:
        return None
        
    session_id = request.cookies.get('session_id')
    if not session_id:
        return None
        
    return redis_client.get(f"ctf:e2e:session:{session_id}")

def aes_gcm_decrypt(key, iv, ciphertext, tag):
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
    decryptor = cipher.decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()

def aes_gcm_encrypt(key, plaintext):
    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return iv, ciphertext, encryptor.tag

def e2e_before_request():
    # Skip endpoints that shouldn't be encrypted
    if request.path.startswith('/api/e2e/') or request.path.startswith('/api/leaderboard'):
        return
        
    # We only decrypt POST/PUT data
    if request.method in ['POST', 'PUT', 'PATCH']:
        if not request.is_json:
            return
            
        data = request.get_json(silent=True) or {}
        if 'e2e_payload' in data:
            key = get_session_key()
            if not key:
                return
                
            try:
                payload_parts = data['e2e_payload'].split('.')
                iv = base64.b64decode(payload_parts[0])
                ciphertext = base64.b64decode(payload_parts[1])
                tag = base64.b64decode(payload_parts[2])
                
                decrypted_bytes = aes_gcm_decrypt(key, iv, ciphertext, tag)
                decrypted_json = json.loads(decrypted_bytes.decode('utf-8'))
                
                # Mock the request data
                request._cached_json = (decrypted_json, decrypted_json)
                request.environ['CONTENT_TYPE'] = 'application/json'
            except Exception as e:
                # Decryption failed
                print(f"E2E Decryption Error: {e}")

def e2e_after_request(response):
    # Skip rate limiting 429 and firewall 403
    if response.status_code in [429, 403]:
        return response
        
    # Skip excluded endpoints
    if request.path.startswith('/api/e2e/') or request.path.startswith('/api/leaderboard'):
        return response
        
    # Only encrypt JSON responses
    if response.is_json:
        key = get_session_key()
        if key:
            try:
                plaintext = response.get_data()
                iv, ciphertext, tag = aes_gcm_encrypt(key, plaintext)
                
                encrypted_payload = f"{base64.b64encode(iv).decode()}.{base64.b64encode(ciphertext).decode()}.{base64.b64encode(tag).decode()}"
                
                response.set_data(json.dumps({'e2e_payload': encrypted_payload}))
            except Exception as e:
                print(f"E2E Encryption Error: {e}")
                
    return response

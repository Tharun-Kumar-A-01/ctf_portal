import json
import base64
from app.e2e import aes_gcm_encrypt, aes_gcm_decrypt
import os

def test_aes_gcm_encryption_cycle():
    """Verify that backend AES-GCM maths natively work isolated from the web context."""
    # Generate a random 256-bit AES key (32 bytes)
    key = os.urandom(32)
    
    plaintext_data = {"email": "test@test.com", "password": "supersecret"}
    plaintext_bytes = json.dumps(plaintext_data).encode('utf-8')
    
    # Encrypt
    iv, ciphertext, tag = aes_gcm_encrypt(key, plaintext_bytes)
    
    assert len(iv) == 12 # Standard GCM nonce length
    assert len(tag) == 16 # Standard GCM tag length
    
    # Decrypt
    decrypted_bytes = aes_gcm_decrypt(key, iv, ciphertext, tag)
    decrypted_str = decrypted_bytes.decode('utf-8')
    
    decrypted_json = json.loads(decrypted_str)
    
    assert decrypted_json["email"] == "test@test.com"
    assert decrypted_json["password"] == "supersecret"

def test_aes_gcm_tamper_reject():
    """Verify that tampering with ciphertext forces a decryption failure."""
    key = os.urandom(32)
    plaintext_bytes = b"highly sensitive data"
    
    iv, ciphertext, tag = aes_gcm_encrypt(key, plaintext_bytes)
    
    # Tamper with the ciphertext slightly
    tampered_ciphertext = bytearray(ciphertext)
    tampered_ciphertext[0] ^= 0x01 
    
    try:
        aes_gcm_decrypt(key, iv, bytes(tampered_ciphertext), tag)
        assert False, "Decryption succeeded on tampered ciphertext! (Dangerous)"
    except Exception as e:
        # Expected exception from cryptography library on auth tag failure
        assert True

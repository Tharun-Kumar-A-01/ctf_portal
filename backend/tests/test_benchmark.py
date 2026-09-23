import pytest
from app.e2e import aes_gcm_encrypt, aes_gcm_decrypt
import os
import time

def test_encryption_throughput(benchmark):
    """Benchmarks the raw throughput of AES256-GCM context initialization and digestion."""
    key = os.urandom(32)
    plaintext_bytes = b"benchmark string data payload" * 10 
    
    def process_cycle():
        iv, ciphertext, tag = aes_gcm_encrypt(key, plaintext_bytes)
        return aes_gcm_decrypt(key, iv, ciphertext, tag)
        
    result = benchmark.pedantic(process_cycle, rounds=5, iterations=10)
    assert result == plaintext_bytes


def test_api_login_throughput(benchmark, client):
    """Benchmarks the /api/auth/login failure throughput under light load."""
    def make_request():
        res = client.post("/api/auth/login", json={
            "email": "invalid@test.com", 
            "password": "wrong"
        })
        return res.status_code
        
    result = benchmark.pedantic(make_request, rounds=5, iterations=5)
    assert result in [401, 400, 429] 

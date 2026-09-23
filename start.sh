#!/bin/bash
# Generate self-signed TLS certificate if it doesn't exist
mkdir -p /etc/nginx/ssl
if [ ! -f /etc/nginx/ssl/selfsigned.crt ]; then
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/selfsigned.key \
        -out /etc/nginx/ssl/selfsigned.crt \
        -subj "/CN=ctf-platform/O=CTF/C=IN" 2>/dev/null
    echo "[TLS] Self-signed certificate generated."
fi

# Start Nginx in the background
nginx

# Start Flask backend in the foreground with Gunicorn
cd /app/backend

# Generate Master RSA Key for E2E Encryption securely before workers start
mkdir -p /app/backend/instance
if [ ! -f /app/backend/instance/e2e_private_key.pem ]; then
    uv run python3 -c "from cryptography.hazmat.primitives.asymmetric import rsa; from cryptography.hazmat.primitives import serialization; key = rsa.generate_private_key(public_exponent=65537, key_size=2048); open('/app/backend/instance/e2e_private_key.pem', 'wb').write(key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.TraditionalOpenSSL, encryption_algorithm=serialization.NoEncryption()))"
fi

# Initialize DB safely before workers spawn
uv run python init_db.py

# Use exactly the number of cores as requested
workers=$(nproc)
echo "Starting Gunicorn with $workers workers based on $(nproc) cores."
exec uv run gunicorn --bind 127.0.0.1:5000 --workers $workers --threads 10 'run:create_app()'

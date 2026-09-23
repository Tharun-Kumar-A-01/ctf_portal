import os
from datetime import timedelta
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Ensure environment variables are loaded before configuration is evaluated
root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
if os.path.exists(root_env):
    load_dotenv(root_env)
else:
    load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-12345")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key-change-in-production-67890")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    
    # PostgreSQL Database URI
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://ctf_user:ctf_password@ctf-db:5432/ctf_db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Master key for field-level SQLite encryption (AES-256 via Fernet)
    # Generates a default key for dev if not provided
    FERNET_KEY = os.getenv("FERNET_KEY", Fernet.generate_key().decode())
    
    # Valkey Cache URI for Rate Limiter
    CACHE_URL = os.getenv("CACHE_URL", "redis://ctf-cache:6379/0")

from cryptography.fernet import Fernet
from sqlalchemy import TypeDecorator, String, Text

_fernet_instance = None

def init_encryption(key: str):
    global _fernet_instance
    if isinstance(key, str):
        key = key.encode()
    _fernet_instance = Fernet(key)

def get_fernet():
    global _fernet_instance
    if _fernet_instance is None:
        # Fallback key if not explicitly initialized
        key = Fernet.generate_key()
        _fernet_instance = Fernet(key)
    return _fernet_instance

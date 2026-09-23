from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv("CACHE_URL", "redis://ctf-cache:6379/0")
)

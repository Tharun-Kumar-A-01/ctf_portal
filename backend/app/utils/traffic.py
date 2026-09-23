"""
Traffic monitoring utility.

Logs HTTP requests to Redis for historical analysis and real-time streaming.
Uses a batch queue (ctf:traffic_batch) for the WebSocket consumer to drain
in intervals, preventing per-request overhead during DoS attacks.
"""

import json
import time
import threading
from typing import Optional, Set

import redis
from flask import Flask, Response, request, abort

from app.config import Config

# Initialize Valkey/Redis connection
redis_client: Optional[redis.Redis] = None
try:
    # Use strict timeouts for the initial ping so tests/local dev don't hang if Valkey isn't running
    _temp_client = redis.from_url(Config.CACHE_URL, socket_connect_timeout=1, socket_timeout=1)
    _temp_client.ping()
    # Recreate without strict timeouts for production long-polling
    redis_client = redis.from_url(Config.CACHE_URL)
except Exception as e:
    print(f"[WARNING] Valkey cache is unreachable: {e}. Traffic monitoring disabled.")
    redis_client = None

# Maximum entries in the historical log ring buffer
_MAX_HISTORICAL_LOGS: int = 10_000

# In-memory cache for banned IPs to eliminate Redis IO on every request
BANNED_IPS_CACHE: Set[str] = set()

import subprocess
import os

def _update_nginx_banned_ips() -> None:
    try:
        conf_path = '/etc/nginx/dynamic/banned_ips.conf'
        if not os.path.exists('/etc/nginx/dynamic'):
            return # not in container environment where this is set up
            
        with open(conf_path, 'w') as f:
            for ip in BANNED_IPS_CACHE:
                f.write(f"{ip} 1;\n")
                
        subprocess.run(['nginx', '-s', 'reload'], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[SECURITY] Failed to update Nginx banned IPs: {e}")

def _background_worker() -> None:
    """Background thread that syncs banned IPs and processes aggregated traffic."""
    if not redis_client:
        return
        
    try:
        # Initial bulk load for banned IPs
        banned = redis_client.smembers('ctf:banned_ips')
        BANNED_IPS_CACHE.update(ip.decode('utf-8') for ip in banned)
        _update_nginx_banned_ips()
        
        # Subscribe to real-time events
        pubsub = redis_client.pubsub()
        pubsub.subscribe('ctf:traffic_events')
        
        while True:
            try:
                nginx_needs_reload = False
                # 1. Check for pubsub messages (non-blocking)
                msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                while msg:
                    if msg['type'] == 'message':
                        try:
                            event = json.loads(msg['data'].decode('utf-8'))
                            ip = event.get('ip')
                            if ip:
                                if event.get('type') == 'ban':
                                    BANNED_IPS_CACHE.add(ip)
                                    nginx_needs_reload = True
                                elif event.get('type') == 'unban':
                                    BANNED_IPS_CACHE.discard(ip)
                                    nginx_needs_reload = True
                        except Exception as e:
                            print(f"[SECURITY] PubSub parse error: {e}")
                    msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.0)
                
                if nginx_needs_reload:
                    _update_nginx_banned_ips()
                
                # 2. Process aggregated traffic
                # Look for finalized seconds (2 seconds ago ensures all requests for that second have finished)
                ready_sec = int(time.time()) - 2
                
                ready_keys = redis_client.zrangebyscore("ctf:traffic_active_seconds", 0, ready_sec)
                for agg_key_bytes in ready_keys:
                    agg_key = agg_key_bytes.decode('utf-8')
                    # Atomically claim this second using zrem
                    if redis_client.zrem("ctf:traffic_active_seconds", agg_key):
                        raw_data = redis_client.hgetall(agg_key)
                        if raw_data:
                            batch_logs = []
                            agg_timestamp = int(agg_key.split(':')[-1])
                            
                            for signature_bytes, count_bytes in raw_data.items():
                                signature = signature_bytes.decode('utf-8')
                                count = int(count_bytes.decode('utf-8'))
                                
                                parts = signature.split('|')
                                # Signature format: IP|METHOD|PATH|STATUS|AUTH|RATE_LIMITED
                                if len(parts) == 6:
                                    ip_val, method, path, status, auth_str, limit_str = parts
                                    
                                    log_entry = {
                                        'timestamp': agg_timestamp,
                                        'ip': ip_val,
                                        'method': method,
                                        'path': path,
                                        'status_code': int(status),
                                        'is_authenticated': bool(int(auth_str)),
                                        'is_rate_limited': bool(int(limit_str)),
                                        'count': count
                                    }
                                    batch_logs.append(json.dumps(log_entry))
                                
                            if batch_logs:
                                pipe = redis_client.pipeline(transaction=False)
                                for log in batch_logs:
                                    pipe.lpush('ctf:traffic_logs', log)
                                    pipe.rpush('ctf:traffic_batch', log)
                                pipe.ltrim('ctf:traffic_logs', 0, _MAX_HISTORICAL_LOGS - 1)
                                pipe.execute()
                        
                        # Cleanup the hash
                        redis_client.delete(agg_key)

            except Exception as e:
                print(f"[TRAFFIC] Background worker loop error: {e}")
                time.sleep(1)

    except Exception as e:
        print(f"[SECURITY] Worker thread crashed: {e}")

def check_banned_ips() -> None:
    """Before-request hook: abort with 403 if the client IP is banned."""
    ip: str = _extract_client_ip()
    if ip and ip in BANNED_IPS_CACHE:
        abort(403, description="Your IP has been permanently banned from the CTF due to abuse.")


def log_traffic(response: Response) -> Response:
    """
    After-request hook: logs the request to Redis.

    - Appends to ctf:traffic_logs (historical ring buffer).
    - Pushes to ctf:traffic_batch (consumed by WebSocket in batches).
    - Publishes ban/unban events to ctf:traffic_events (real-time PubSub).
    - Manages the automatic strike/ban system.
    """
    if not redis_client:
        return response

    try:
        # Skip logging the traffic monitoring endpoints themselves
        if request.path.startswith('/api/admin/traffic'):
            return response

        ip: str = _extract_client_ip()
        is_authenticated: bool = request.headers.get('Authorization', '').startswith('Bearer ')
        is_rate_limited: bool = response.status_code == 429 or response.status_code == 403

        current_sec = int(time.time())
        signature: str = f"{ip}|{request.method}|{request.path}|{response.status_code}|{int(is_authenticated)}|{int(is_rate_limited)}"
        agg_key: str = f"ctf:traffic_agg:{current_sec}"

        # Increment the counter for this exact signature
        count = redis_client.hincrby(agg_key, signature, 1)

        # If it's the first entry for this second, set expiry and register it
        if count == 1:
            pipe = redis_client.pipeline(transaction=False)
            pipe.expire(agg_key, 60) # Fail-safe expiration
            pipe.zadd("ctf:traffic_active_seconds", {agg_key: current_sec})
            pipe.execute()

        # Strike system for auto-banning abusive IPs
        if is_rate_limited:
            _process_strikes(ip)

    except Exception as e:
        # Fail silently — traffic logging must never crash the request pipeline
        print(f"[TRAFFIC] Logging error: {e}")

    return response


def _extract_client_ip() -> str:
    """Extracts the real client IP from proxy headers."""
    ip: str = request.headers.get('X-Real-IP') or request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()
    return ip or ''


def _process_strikes(ip: str) -> None:
    """Increments strike counter for an IP and auto-bans after threshold."""
    if not redis_client or not ip:
        return

    strike_key: str = f"ctf:strikes:{ip}"
    strikes: int = redis_client.incr(strike_key)
    if strikes == 1:
        redis_client.expire(strike_key, 60)  # Strikes expire after 60 seconds

    if strikes >= 5:
        # Optimistically add to local cache before Redis syncs
        BANNED_IPS_CACHE.add(ip)
        redis_client.sadd('ctf:banned_ips', ip)
        # Ban events use PubSub for immediate delivery
        redis_client.publish('ctf:traffic_events', json.dumps({
            "type": "ban",
            "ip": ip
        }))
        print(f"[SECURITY] Auto-banned IP {ip} due to excessive rate limiting.")


def init_traffic_monitor(app: Flask) -> None:
    """Registers traffic monitoring hooks on the Flask app."""
    # Start the background sync thread
    if redis_client:
        sync_thread = threading.Thread(target=_background_worker, daemon=True)
        sync_thread.start()
        
    app.before_request(check_banned_ips)
    app.after_request(log_traffic)

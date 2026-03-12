import redis
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

TTL_SECONDS = 86400  # 24 hours

def _make_key(query: str) -> str:
    # Hash the query so special characters dont cause issues
    return "insightstream:" + hashlib.md5(query.encode()).hexdigest()

def get_cached(query: str):
    key = _make_key(query)
    result = client.get(key)
    if result:
        return result.decode('utf-8')
    return None

def set_cached(query: str, report: str):
    key = _make_key(query)
    client.setex(key, TTL_SECONDS, report.encode('utf-8'))

def clear_cache():
    # Useful for testing — clears all insightstream keys
    keys = client.keys("insightstream:*")
    if keys:
        client.delete(*keys)
    return len(keys)

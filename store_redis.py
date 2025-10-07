import os, time, logging
from upstash_redis import Redis

log = logging.getLogger("redis-store")

# Connect to Upstash Redis using environment variables from Render
REDIS = Redis(
    url=os.environ["UPSTASH_REDIS_REST_URL"],
    token=os.environ["UPSTASH_REDIS_REST_TOKEN"]
)

def save_message(user_id: int, text: str):
    """Save a text message from a user as a simple key-value pair."""
    key = f"msg:{user_id}:{int(time.time())}"
    REDIS.set(key, text)
    log.info(f"Saved message to Redis: {key}")

def get_messages(user_id: int, limit: int = 20):
    """Fetch recent messages of the user (by timestamp order)."""
    pattern = f"msg:{user_id}:*"
    keys = REDIS.keys(pattern)
    keys = sorted(keys, reverse=True)[:limit]
    return [REDIS.get(k) for k in keys]

def clear_messages(user_id: int) -> int:
    """Remove all message keys for a specific user."""
    pattern = f"msg:{user_id}:*"
    keys = REDIS.keys(pattern)
    if not keys:
        return 0
    for k in keys:
        REDIS.delete(k)
    log.info(f"Deleted {len(keys)} messages for user {user_id}")
    return len(keys)

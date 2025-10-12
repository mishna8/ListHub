import os, time, logging
from upstash_redis import Redis
import json,  uuid

log = logging.getLogger("redis-store")

# Connect to Upstash Redis using environment variables from Render
REDIS = Redis(
    url=os.environ["UPSTASH_REDIS_REST_URL"],
    token=os.environ["UPSTASH_REDIS_REST_TOKEN"]
)

### personal list handles 
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

#### default shared list handles 
def add_shared_item(text: str, user_id: int):
    """Add a new item to the shared to-do list."""
    item = {
        "id": str(uuid.uuid4())[:8],  # short unique id
        "text": text,
        "done": False,
        "created_by": user_id,
        "created_at": int(time.time())
    }
    REDIS.rpush("todo:shared", json.dumps(item, ensure_ascii=False))
    log.info(f"Added shared item: {item['id']} -> {text}")
    return item["id"]

def get_shared_items(limit: int = 100):
    """Return all items from the shared to-do list (up to 'limit')."""
    rows = REDIS.lrange("todo:shared", 0, limit)
    items = []
    for r in rows:
        try:
            items.append(json.loads(r))
        except Exception:
            continue
    return items

def set_item_done(index: int, done: bool = True):
    """Mark item by its position (1-based index) as done/undone."""
    rows = REDIS.lrange("todo:shared", 0, -1)
    if index < 1 or index > len(rows):
        return False
    items = [json.loads(r) for r in rows]
    items[index - 1]["done"] = done
    # rewrite list
    REDIS.delete("todo:shared")
    for it in items:
        REDIS.rpush("todo:shared", json.dumps(it, ensure_ascii=False))
    return True

def delete_shared_item(index: int):
    """Delete an item from the shared list by its position (1-based)."""
    rows = REDIS.lrange("todo:shared", 0, -1)
    if index < 1 or index > len(rows):
        return False
    del rows[index - 1]
    REDIS.delete("todo:shared")
    for r in rows:
        REDIS.rpush("todo:shared", r)
    log.info(f"Deleted shared item index {index}")
    return True

def clear_shared_items():
    """Delete the entire shared to-do list."""
    REDIS.delete("todo:shared")
    log.info("Cleared shared to-do list")
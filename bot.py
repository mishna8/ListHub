# bot.py — Shared list (2 users), JSON + GitHub Gist persistence, Israel timezone
# Notes:
# - Does NOT drop pending Telegram updates on wake (good for Render Free sleep)
# - Saves data to a local JSON file (ephemeral) AND to a private GitHub Gist (persistent)
# - ENV required: BOT_TOKEN, GITHUB_TOKEN (classic PAT with 'gist' scope). Optional: GIST_ID, GIST_FILENAME, GIST_DESCRIPTION, DATA_PATH.

import os, re, string,  random
import json
import time

import telebot
from telebot.types import Message

from flask import Flask, request, abort
import logging
from html import escape as esc
from upstash_redis import Redis
import store_redis

# region settings

# --- Logging (נוח לדיבוג ברנדר) ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("hello-bot")

# --- Env Variables ---

#BOT_TOKEN = "8468655841:AAEFFgX96L50KuL4BvNECI_Reuoq8YYOYWQ" 
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "")
if not re.match(r"^\d+:[A-Za-z0-9_-]+$", BOT_TOKEN):
    raise RuntimeError("BOT_TOKEN is missing or malformed.")

#APP_URL = "https://listhub-cw6o.onrender.com"
APP_URL   = os.environ["APP_URL"]

# SECRET is a custom random string used as part of the webhook URL for security 
# a made up string that only Telegram will know it - APP_URL/IloveLizzy_theBestPuppyEver
SECRET    = os.environ["WEBHOOK_SECRET"]

# ---- ALLOW LIST ----
ALLOWED = {1317349810, 816672824}

def allowed(user_id: int) -> bool:
    return user_id in ALLOWED

#endregion

# region redis db handle 

# Connect to Upstash Redis via REST (env vars must be set in Render)
REDIS = Redis(
    url=os.environ["UPSTASH_REDIS_REST_URL"],
    token=os.environ["UPSTASH_REDIS_REST_TOKEN"]
)

# Namespace prefix for keys (helps you isolate environments/projects)
PREFIX = os.environ.get("REDIS_PREFIX", "tb") 

#Build a namespaced Redis key.
def _k(*parts: str) -> str:
    return f"{PREFIX}:" + ":".join(parts)

#Convert integer to a compact base36 string (for shorter IDs).
def _base36(n: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0: return "0"
    s = []
    while n:
        n, r = divmod(n, 36)
        s.append(chars[r])
    return "".join(reversed(s))

#Generate a short unique-ish ID using timestamp+random.
def new_id() -> str:
    ts = int(time.time() * 1000)
    rnd = "".join(random.choices(string.ascii_lowercase + string.digits, k=3))
    return _base36(ts) + rnd 

 #   Create a new item and update minimal indexes:
 #   - item:{id} (String JSON)
 #   - list:{L}:by_due (ZSET; here we store 0 due for now)
 #   - list:{L}:by_updated (ZSET; score = updated timestamp)
 #   - list:{L}:status:todo (SET membership)
def create_item(list_id: str, owner: int, title: str, tags=None, due_ts: int = 0, status: str = "todo") -> str:

    tags = tags or []
    now = int(time.time())
    _id = new_id()
    item_key = _k("item", _id)

    item = {
        "id": _id,
        "title": title,
        "status": status,        # todo/doing/done
        "tags": tags,            # ["work","home"]
        "due": due_ts,           # unix seconds (0=none)
        "updated": now,
        "list": list_id,        
        "owner": owner
    }

    # Main write
    REDIS.set(item_key, json.dumps(item, ensure_ascii=False))

    # Indexes
    REDIS.zadd(_k("list", list_id, "by_due"), { _id: float(due_ts) })
    REDIS.zadd(_k("list", list_id, "by_updated"), { _id: float(now) })
    REDIS.sadd(_k("list", list_id, "status", status), _id)
    for t in tags:
        REDIS.sadd(_k("list", list_id, "tag", t), _id)

    return _id

#    Return latest items by 'updated' (newest first).
#    Uses ZREVRANGE when available; falls back to ZRANGE + reverse if needed.
#    Fetches item bodies in bulk via MGET to minimize command count.

def get_recent_items(list_id: str, limit: int = 50):
    try:
        ids = REDIS.zrevrange(_k("list", list_id, "by_updated"), 0, max(0, limit - 1))
    except Exception:
        ids = REDIS.zrange(_k("list", list_id, "by_updated"), 0, max(0, limit - 1))
        ids = list(reversed(ids))

    if not ids:
        return []

    keys = [_k("item", i) for i in ids]
    rows = REDIS.mget(*keys)
    items = [json.loads(x) for x in rows if x]

    # Ensure final order is newest first
    items.sort(key=lambda it: it.get("updated", 0), reverse=True)
    return items

#def get_page_by_due(list_id: str, start: float = "-inf", end: float = "+inf", offset: int = 0, count: int = 20):
#    """
#    מחזיר עמוד פריטים לפי due (עולה). סינונים (סטטוס/תגיות) אפשר לבצע בקוד אחרי MGET.
#    """
#    ids = REDIS.zrangebyscore(_k("list", list_id, "by_due"), start, end, offset=offset, count=count)
#    if not ids:
#        return []
#    # MGET על כל ה-items במכה אחת — חסכון פקודות
#    keys = [_k("item", i) for i in ids]
#    rows = REDIS.mget(*keys)
#    items = [json.loads(x) for x in rows if x]
#    # ממיינים שוב לפי due ליתר ביטחון
#    items.sort(key=lambda it: (it.get("due", 0), it.get("updated", 0)))
#    return items
#
#def update_status(list_id: str, item_id: str, new_status: str):
#    """מעביר סטטוס ומעדכן אינדקסים"""
#    item_key = _k("item", item_id)
#    raw = REDIS.get(item_key)
#    if not raw:
#        return False
#    it = json.loads(raw)
#    old_status = it.get("status", "todo")
#    if new_status != old_status:
#        REDIS.srem(_k("list", list_id, "status", old_status), item_id)
#        REDIS.sadd(_k("list", list_id, "status", new_status), item_id)
#        it["status"] = new_status
#    it["updated"] = int(time.time())
#    REDIS.set(item_key, json.dumps(it, ensure_ascii=False))
#    REDIS.zadd(_k("list", list_id, "by_updated"), { item_id: float(it["updated"]) })
#    return True
#
#def add_tags(list_id: str, item_id: str, tags):
#    item_key = _k("item", item_id)
#    raw = REDIS.get(item_key)
#    if not raw:
#        return False
#    it = json.loads(raw)
#    existing = set(it.get("tags", []))
#    for t in tags:
#        if t not in existing:
#            existing.add(t)
#            REDIS.sadd(_k("list", list_id, "tag", t), item_id)
#    it["tags"] = list(existing)
#    it["updated"] = int(time.time())
#    REDIS.set(item_key, json.dumps(it, ensure_ascii=False))
#    REDIS.zadd(_k("list", list_id, "by_updated"), { item_id: float(it["updated"]) })
#    return True



#endregion 



# --- Bot ------------------------------------------------------------------------------------
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app  = Flask(__name__)


# region bot actions
#---START
@bot.message_handler(commands=["start", "help"])
def on_start(message: Message):
    uid = message.from_user.id
    log.info(f"/start from uid={uid}, username={message.from_user.username}")
    if not allowed(uid):
        bot.reply_to(message, "❌ לא מורשה להשתמש בבוט הזה")
    bot.reply_to(message, "WELCOM SHLOMIT <3")

#---ON TEXT
@bot.message_handler(content_types=["text"])
def on_text(message):
    uid = message.from_user.id
    if not allowed(uid):
        bot.reply_to(message, "❌ Not authorized to use this bot")
        return

    text = (message.text or "").strip()

    # If user sends "?", return their recent items from Redis
    if text == "?":
        list_id = f"user:{uid}:inbox"
        try:
            items = store_redis.get_recent_items(list_id, limit=50)
        except Exception as e:
            log.error(f"Redis read failed: {e}")
            bot.reply_to(message, "⚠️ Redis read error")
            return

        if not items:
            bot.reply_to(message, "No items saved yet.")
            return

        # Build a compact textual list (truncate long titles)
        lines = []
        for it in items:
            title = it.get("title", "")
            if len(title) > 80:
                title = title[:77] + "..."
            lines.append(f"• {esc(title)}")

        out = "\n".join(lines)

        # Telegram hard limit ~4096 chars — keep some headroom
        if len(out) > 3800:
            out = out[:3797] + "..."

        bot.reply_to(message, out)
        return

    # Otherwise: save every incoming text as a new "inbox" item for this user
    list_id = f"user:{uid}:inbox"
    try:
        store_redis.create_item(list_id=list_id, owner=uid, title=text)
    except Exception as e:
        log.error(f"Redis save failed: {e}")

    bot.reply_to(message, "HELLOW WORLD")


@app.route(f"/{SECRET}", methods=["POST"])
def telegram_webhook():
    if request.headers.get("content-type") != "application/json":
        abort(403)
    update = telebot.types.Update.de_json(request.get_data(as_text=True))
    bot.process_new_updates([update])
    return "OK", 200
#endregion 


# region main 
if __name__ == "__main__":
    # Disconnect any old webhooks and then set a new one to APP_URL/SECRET
    try: bot.remove_webhook()
    except: pass
    bot.set_webhook(url=f"{APP_URL}/{SECRET}")
    # Render requires listening to $PORT
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))

#--MAIN FUNC
#def run_polling():
#    """
#    Polling שמחזיק אחרי שינה של Render:
#    - לא מוחקים pending updates (skip_pending=False)
#    - webhook מבוטל מראש (remove_webhook)
#    - timeout סביר כדי שלא להיתקע יותר מדי זמן
#    - לולאות ניסיון כדי להתאושש מניתוקי רשת קצרים
#    """
#    # cancel all webhooks if we had any
#    try:
#        bot.remove_webhook()
#    except Exception as e:
#        log.warning(f"remove_webhook failed: {e}")
#
#    # pull any percistent data from (JSON/Gist/Redis)
#    # render will flush when redeploy
#    # try:
#    #     load_store()
#    # except Exception as e:
#    #     log.warning(f"load_store failed: {e}")
#
#    log.info("Starting bot... (Ctrl+C to stop)")
#    while True:
#        try:
#            # skip_pending=False => Collecting message queue after sleep
#            # long_polling_timeout - Short, to release connection from time to time
#            bot.infinity_polling(
#                skip_pending=False,
#                timeout=20,
#                long_polling_timeout=20,
#                logger_level=logging.INFO,
#            )
#        except KeyboardInterrupt:
#            log.info("Shutting down by KeyboardInterrupt")
#            break
#        except Exception as e:
#            # אם נפלה תקלה זמנית ברשת/CPU — נחכה מעט ונחזור לפולינג
#            log.error(f"Polling error: {e}. Retrying in 3s...")
#            time.sleep(3)
#
#if __name__ == "__main__":
#    run_polling()
   
#endregion




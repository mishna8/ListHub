# bot.py — Shared list (2 users), JSON + GitHub Gist persistence, Israel timezone
# Notes:
# - Does NOT drop pending Telegram updates on wake (good for Render Free sleep)
# - Saves data to a local JSON file (ephemeral) AND to a private GitHub Gist (persistent)
# - ENV required: BOT_TOKEN, GITHUB_TOKEN (classic PAT with 'gist' scope). Optional: GIST_ID, GIST_FILENAME, GIST_DESCRIPTION, DATA_PATH.

import os, re, json, threading, requests
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
import telebot
from telebot import formatting
from io import BytesIO

#the token is env on render
#BOT_TOKEN = "8468655841:AAEFFgX96L50KuL4BvNECI_Reuoq8YYOYWQ" 
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip().strip('"').strip("'")
if not re.match(r"^\d+:[A-Za-z0-9_-]+$", BOT_TOKEN):
    raise RuntimeError("BOT_TOKEN is missing or malformed.")

# ---- ALLOW LIST ----
ALLOWED = {1317349810, 816672824}

def allowed(user_id: int) -> bool:
    return user_id in ALLOWED

# ----- Timezones (store UTC, display Israel time) -----
TZ_IL = ZoneInfo("Asia/Jerusalem")
TZ_UTC = ZoneInfo("UTC")

def utc_now_str_min() -> str:
    return datetime.now(TZ_UTC).replace(second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")

def fmt_local_from_utc_str(s: str) -> str:
    dt_utc = datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=TZ_UTC)
    return dt_utc.astimezone(TZ_IL).strftime("%Y-%m-%d %H:%M")

# ----- Local JSON file (ephemeral on Render) -----
DATA_PATH = os.getenv("DATA_PATH", "data.json")

# ----- GitHub Gist (classic PAT, no expiration if you prefer) -----
GITHUB_TOKEN = (os.getenv("GITHUB_TOKEN") or "").strip().strip('"').strip("'")
GIST_ID       = (os.getenv("GIST_ID") or "").strip()                       # If empty: a new Gist will be created on first boot
GIST_FILENAME = (os.getenv("GIST_FILENAME") or "todo_store.json").strip()
GIST_DESC     = (os.getenv("GIST_DESCRIPTION") or "ListHub bot data").strip()
GIST_API      = "https://api.github.com/gists"

def gh_headers():
    if not GITHUB_TOKEN:
        return {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

def gist_create(initial_text: str) -> str:
    payload = {"description": GIST_DESC, "public": False, "files": {GIST_FILENAME: {"content": initial_text}}}
    r = requests.post(GIST_API, headers=gh_headers(), json=payload, timeout=20)
    r.raise_for_status()
    gid = r.json()["id"]
    print(f"[INFO] Created new Gist: {gid}")
    return gid

def gist_update(gist_id: str, text: str) -> None:
    payload = {"files": {GIST_FILENAME: {"content": text}}}
    r = requests.patch(f"{GIST_API}/{gist_id}", headers=gh_headers(), json=payload, timeout=20)
    r.raise_for_status()

def gist_get(gist_id: str) -> Optional[str]:
    r = requests.get(f"{GIST_API}/{gist_id}", headers=gh_headers(), timeout=20)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    js = r.json()
    file = (js.get("files") or {}).get(GIST_FILENAME)
    if not file:
        return None
    return file.get("content")

# ----- In-memory store + thread-safety -----
LOCK = threading.Lock()
store = {"next_id": 1, "items": []}
# item shape: { "id": int, "text": str, "created_at_utc": "YYYY-MM-DD HH:MM", "added_by": int }

def load_store() -> None:
    """Boot order: Gist (if token+id) -> create new Gist (if token, no id) -> local file -> empty."""
    global GIST_ID
    # 1) Load from Gist if token+id
    if GITHUB_TOKEN and GIST_ID:
        try:
            content = gist_get(GIST_ID)
            if content:
                data = json.loads(content)
                with LOCK:
                    store.clear(); store.update(data)
                print(f"[INFO] Loaded store from Gist {GIST_ID} ({len(store.get('items', []))} items)")
                return
        except Exception as e:
            print("[WARN] Gist load failed, will try local file:", e)
    # 2) Create new Gist if token present but no ID
    if GITHUB_TOKEN and not GIST_ID:
        try:
            init_text = json.dumps(store, ensure_ascii=False, indent=2)
            GIST_ID = gist_create(init_text)
            print("[WARN] Please set env GIST_ID to persist across deploys:", GIST_ID)
        except Exception as e:
            print("[WARN] Gist create failed, will try local file:", e)
    # 3) Local file (ephemeral)
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            with LOCK:
                store.clear(); store.update(data)
            print(f"[INFO] Loaded store from local file ({len(store.get('items', []))} items)")
            return
        except Exception as e:
            print("[WARN] Local load failed, starting fresh:", e)
    # 4) Empty
    with LOCK:
        store.clear(); store.update({"next_id": 1, "items": []})
    print("[INFO] Started with empty store")

def save_store() -> None:
    """Save atomically to local file (optional) and update Gist if configured."""
    txt = json.dumps(store, ensure_ascii=False, indent=2)
    # Local file (ephemeral)
    try:
        tmp = DATA_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(txt)
        os.replace(tmp, DATA_PATH)
    except Exception as e:
        print("[WARN] local save failed:", e)
    # Gist (persistent)
    if GITHUB_TOKEN and GIST_ID:
        try:
            gist_update(GIST_ID, txt)
        except Exception as e:
            print("[WARN] Gist update failed:", e)

# ----- Bot setup -----
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

@bot.message_handler(commands=["start"])
def start(m: telebot.types.Message):
    uid = m.from_user.id
    if not allowed(uid):
        return bot.reply_to(m, f"הבוט פרטי. אין לך הרשאה.\nה-ID שלך: {uid}")
    msg = "היי! כל הודעת טקסט מוסיפה פריט לרשימה המשותפת.\nפקודות: /list"
    if GITHUB_TOKEN and not GIST_ID:
        msg += "\n⚠️ נוצר Gist חדש. מומלץ להגדיר GIST_ID ב-Render כדי לקבע בין דפלויים."
    bot.reply_to(m, msg)

@bot.message_handler(commands=["list"])
def list_items(m: telebot.types.Message):
    uid = m.from_user.id
    if not allowed(uid):
        return bot.reply_to(m, f"הבוט פרטי. אין לך הרשאה.\nה-ID שלך: {uid}")
    with LOCK:
        rows = list(reversed(store["items"]))[:20]
    if not rows:
        return bot.reply_to(m, "אין עדיין פריטים.")
    lines = []
    for it in rows:
        created_local = fmt_local_from_utc_str(it["created_at_utc"])
        txt = formatting.escape_html(it["text"])
        lines.append(f"• <b>#{it['id']}</b> {txt} — {created_local} ע\"י {it['added_by']}")
    bot.reply_to(m, "\n".join(lines))

@bot.message_handler(func=lambda msg: True, content_types=["text"])
def add_item(m: telebot.types.Message):
    uid = m.from_user.id
    if not allowed(uid):
        return bot.reply_to(m, f"הבוט פרטי. אין לך הרשאה.\nה-ID שלך: {uid}")
    text = (m.text or "").strip()
    if not text:
        return
    created_utc = utc_now_str_min()
    with LOCK:
        iid = store["next_id"]; store["next_id"] += 1
        store["items"].append({"id": iid, "text": text, "created_at_utc": created_utc, "added_by": uid})
        save_store()
    bot.reply_to(m, "✅")

if __name__ == "__main__":
    print("Starting bot... (Ctrl+C to stop)")
    load_store()
    # Important for Render Free: DO NOT drop pending updates; collect them after wake
    bot.remove_webhook()                    # <-- don't pass drop_pending_updates=True
    bot.infinity_polling(skip_pending=False)  # <-- collect queued messages after sleep, to discard change to true

# pip install pyTelegramBotAPI
import os, json, datetime
from typing import List, Dict, Union
import re
import telebot

#the token is env on render
#BOT_TOKEN = "8468655841:AAEFFgX96L50KuL4BvNECI_Reuoq8YYOYWQ" 
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip().strip('"').strip("'")
if not re.match(r"^\d+:[A-Za-z0-9_-]+$", BOT_TOKEN):
    raise RuntimeError("BOT_TOKEN is missing or malformed. Set it in Render → Environment without quotes.")

# ---- ALLOW LIST ----
ALLOWED = {1317349810, 816672824}  # שימי כאן את המספרים האמיתיים

def allowed(user_id: int) -> bool:
    return user_id in ALLOWED

# ---- אחסון מקומי ----
DATA_FILE = "data.json"
# מבנה: {"<user_id>": [ { "text": str, "created_at": iso }, ... ]}
store: Dict[str, List[dict]] = {}

def load_json():
    """טוען קובץ קיים ותומך גם במבנה הישן של מחרוזות בלבד."""
    global store
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    new_store: Dict[str, List[dict]] = {}
                    for k, v in data.items():
                        lst = []
                        if isinstance(v, list):
                            for item in v:
                                if isinstance(item, dict) and "text" in item:
                                    lst.append(item)
                                elif isinstance(item, str):
                                    # תאימות לאחור: פריט ישן בלי תאריך
                                    lst.append({"text": item, "created_at": None})
                        new_store[str(k)] = lst
                    store = new_store
        except Exception as e:
            print("[WARN] load_json failed:", e)

def save_json():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[WARN] save_json failed:", e)

load_json()

def now_utc_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def get_todos(user_id: int) -> List[dict]:
    return store.get(str(user_id), [])

def add_todos(user_id: int, items: List[str]) -> int:
    items = [i.strip() for i in items if i.strip()]
    if not items:
        return 0
    lst = store.setdefault(str(user_id), [])
    for txt in items:
        lst.append({"text": txt, "created_at": now_utc_iso()})
    save_json()
    return len(items)

def delete_todo(user_id: int, index: int) -> str:
    """מוחק פריט לפי אינדקס (1 מבוסס)"""
    lst = store.get(str(user_id), [])
    if not lst:
        return "הרשימה ריקה ✨"
    if index < 1 or index > len(lst):
        return f"אין פריט מספר {index} ברשימה."
    removed = lst.pop(index - 1)
    save_json()
    return f"❌ נמחק הפריט: {removed.get('text','')}"

# ---- תגובת אמוג'י (אם נתמך) ----
def try_react(bot, chat_id: int, message_id: int, emoji: str = "✅"):
    try:
        if hasattr(telebot.types, "ReactionTypeEmoji"):
            rt = telebot.types.ReactionTypeEmoji(emoji=emoji)
            bot.set_message_reaction(chat_id=chat_id, message_id=message_id, reaction=[rt], is_big=False)
    except Exception:
        pass

# ---- הבוט ----
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

@bot.message_handler(commands=['start'])
def start(m: telebot.types.Message):
    uid = m.from_user.id
    print(f"[INFO] /start from {uid} - {m.from_user.first_name} ({m.from_user.username})")
    if not allowed(uid):
        return bot.reply_to(m, f"הבוט פרטי. אין לך הרשאה.\nה-ID שלך: {uid}")
    bot.reply_to(m,
        "WELCOM SHLOMIT\n"
        "This is my ListHub app for keeping to do  lists\n"
        "just text and it will add your items\n"
        "text ? to get the current list and text -[number] to remove the item"
    )

@bot.message_handler(content_types=['text'])
def on_text(m: telebot.types.Message):
    uid = m.from_user.id
    if not allowed(uid):
        return

    text = (m.text or "").strip()
    if not text:
        return

    # הצגת הרשימה
    if text == "?":
        items = get_todos(uid)
        if not items:
            return bot.reply_to(m, "הרשימה ריקה ✨")
        lines = []
        for i, it in enumerate(items, start=1):
            created = it.get("created_at") or ""
            # נציג בפורמט קומפקטי; אם נרצה המרה לאזור זמן בעתיד – נוסיף ספרייה.
            lines.append(f"{i}. {it.get('text','')}  <i>({created})</i>")
        return bot.reply_to(m, "To-Do:\n" + "\n".join(lines))

    # מחיקה: '-<מספר>'
    m_del = re.match(r"^\s*[-־–—]\s*(\d+)\s*$", text)
    if m_del:
        idx = int(m_del.group(1))
        result = delete_todo(uid, idx)
        return bot.reply_to(m, result)

    # דיפולט: הוספה (תומך בכמה שורות)
    raw_items = [ln.strip() for ln in text.splitlines() if ln.strip()]
    added = add_todos(uid, raw_items)
    if added > 0:
        try_react(bot, m.chat.id, m.message_id, "✅")
        return bot.reply_to(m, f"✅ נוספו {added} פריטים ל-To-Do")
    else:
        return bot.reply_to(m, "לא זוהו פריטים להוספה.")

if __name__ == "__main__":
    print("Starting bot... (Ctrl+C to stop)")
    bot.infinity_polling(skip_pending=True)

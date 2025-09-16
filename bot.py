# pip install pyTelegramBotAPI
import os, json
from typing import List, Dict
import telebot

BOT_TOKEN = "8468655841:AAEFFgX96L50KuL4BvNECI_Reuoq8YYOYWQ" # os.getenv("BOT_TOKEN") or "PASTE_YOUR_TOKEN"
bot = telebot.TeleBot(BOT_TOKEN)

# ---- ALLOW LIST ----
ALLOWED = {1317349810}  # שימי כאן את המספרים האמיתיים

def allowed(user_id: int) -> bool:
    return user_id in ALLOWED

# ---- אחסון מקומי (JSON) ----
DATA_FILE = "data.json"
# מבנה: {"<user_id>": ["item1", "item2", ...]}
store: Dict[str, List[str]] = {}

def load_json():
    global store
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # וודאי שכל ערך הוא list
                    store = {str(k): list(v) for k, v in data.items()}
        except Exception as e:
            print("[WARN] load_json failed:", e)

def save_json():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[WARN] save_json failed:", e)

load_json()

def get_todos(user_id: int) -> List[str]:
    return store.get(str(user_id), [])

def add_todos(user_id: int, items: List[str]) -> int:
    items = [i.strip() for i in items if i.strip()]
    if not items:
        return 0
    lst = store.setdefault(str(user_id), [])
    lst.extend(items)
    save_json()
    return len(items)

# ---- ניסיון לשים תגובת אימוג’י (אם הספרייה תומכת; אם לא, מתעלמים בשקט) ----
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
    bot.reply_to(m, f"היי {m.from_user.first_name}! את/ה ברשימת ההרשאות ✅")
    
@bot.message_handler(content_types=['text'])
def on_text(m: telebot.types.Message):
    uid = m.from_user.id
    if not allowed(uid):
        return  # מתעלמים מלא-מורשים

    text = (m.text or "").strip()
    if not text:
        return

    # הצגת הרשימה
    if text == "?":
        items = get_todos(uid)
        if not items:
            return bot.reply_to(m, "הרשימה ריקה ✨")
        lines = [f"{i+1}. {it}" for i, it in enumerate(items)]
        return bot.reply_to(m, "To-Do:\n" + "\n".join(lines))

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




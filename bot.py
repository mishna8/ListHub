# bot.py — Shared list (2 users), hosted on render, redis DB 
# - on text saves toDo item
# - ? returns all items on list
# - /clear deletss all items on list
# - /del <num> deletes specific item on list
# - /done <num> checks specific item on list 


import os, re, string,  random

import telebot
from telebot.types import Message, types

from flask import Flask, request, abort
import logging
from html import escape as esc
import store_redis

# region settings

# ---- Logging  ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("hello-bot")

# ---- Env Variables ---

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


# ---- Bot ------------------------------------------------------------------------------------
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app  = Flask(__name__)


# region bot inline buttons 
@bot.callback_query_handler(func=lambda call: True)
def on_callback(call):
    """Handle all button actions."""
    try:
        if call.data == "clear_done":
            removed = store_redis.delete_done_items()
            bot.answer_callback_query(call.id, "🧹 Done!")
            bot.send_message(
                call.message.chat.id,
                f"🧹 Deleted {removed} done items." if removed else "✨ No done items to delete."
            )
        # ... (other callback handlers like done:/del:)
    except Exception as e:
        log.error(f"Callback error: {e}")
        bot.answer_callback_query(call.id, "⚠️ Error occurred.")

#endregion 


# region bot actions
#---START
@bot.message_handler(commands=["start", "help"])
def on_start(message: Message):
    uid = message.from_user.id
    log.info(f"/start from uid={uid}, username={message.from_user.username}")
    if not allowed(uid):
        bot.reply_to(message, "❌ Not authorized to use this bot")
    bot.reply_to(message, "WELCOM SHLOMIT <3")

#---ON CLEAR
@bot.message_handler(commands=["clear"])
def on_clear(message: Message):
    uid = message.from_user.id
    log.info(f"/clear from uid={uid}, username={message.from_user.username}")
    if not allowed(uid):
        bot.reply_to(message, "❌ Not authorized to use this bot")
        return
    
    #Delete all stored messages for the current user
    try:
        deleted = store_redis.clear_shared_items()
        bot.reply_to(
            message,
            f"Cleared {deleted} saved messages."
        )
        log.info(f"User {uid} cleared {deleted} messages from Redis")
    except Exception as e:
        log.error(f"Redis clear failed: {e}")
        bot.reply_to(message, "⚠️ Failed to clear messages from Redis.")

#---ON DEL 
@bot.message_handler(commands=["del"])
def on_delete(message: Message):
    uid = message.from_user.id
    log.info(f"/del from uid={uid}, username={message.from_user.username}")
    if not allowed(uid):
        bot.reply_to(message, "❌ Not authorized to use this bot")
        return

    #Delete the specific item in the text
    try:
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            bot.reply_to(message, "Usage: /del <number>")
            return
        idx = int(parts[1])
        ok = store_redis.delete_shared_item(idx)
        bot.reply_to(message, "🗑️ Deleted item." if ok else "Item not found.")
    except Exception as e:
        log.error(f"/del error: {e}")
        bot.reply_to(message, "⚠️ Failed to delete item.")

#---ON DONE
@bot.message_handler(commands=["done"])
def on_done(message: Message):
    uid = message.from_user.id
    log.info(f"/done from uid={uid}, username={message.from_user.username}")
    if not allowed(uid):
        bot.reply_to(message, "❌ Not authorized to use this bot")
        return

    #Change the status of the specif item too done
    try:
        parts = message.text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            bot.reply_to(message, "Usage: /done <number>")
            return
        idx = int(parts[1])
        ok = store_redis.set_item_done(idx, done=True)
        bot.reply_to(message, "✅ Marked as done." if ok else "Item not found.")
    except Exception as e:
        log.error(f"/done error: {e}")
        bot.reply_to(message, "⚠️ Failed to update item.")

#---ON CLEAN
@bot.message_handler(commands=["clean", "clear_done"])
def on_clear_done(message):
    uid = message.from_user.id
    log.info(f"/clean from uid={uid}, username={message.from_user.username}")
    if not allowed(uid):
        bot.reply_to(message, "❌ Not authorized to use this bot")
        return

    #Delete items marked as done
    removed = store_redis.delete_done_items()
    if removed == 0:
        bot.reply_to(message, "✨ No done items to delete.")
    else:
        bot.reply_to(message, f"🧹 Deleted {removed} done items.")


#---ON TEXT + ? -----------------------------
# must be last so handler will fail to compare all commands and only then get here 
@bot.message_handler(content_types=["text"])
def on_text(message):
    uid = message.from_user.id
    log.info(f"text from uid={uid}, username={message.from_user.username}")
    if not allowed(uid):
        bot.reply_to(message, "❌ Not authorized to use this bot")
        return

    text = (message.text or "").strip()

    # If the user sends '?', return saved items
    if text == "?":
        try:
            items = store_redis.get_shared_items()
            if not items:
                bot.reply_to(message, "To Do List is empty")
                return
            
            lines = []
            for i, it in enumerate(items, start=1):
                mark = "✅" if it.get("done") else "⬜"
                text = f"~{it['text']}~" if it.get("done") else it["text"]
                lines.append(f"{i}. {mark} {text}")
            reply = "🗒️ To-Do List:\n" + "\n".join(lines)
            bot.reply_to(message, reply)
            
            # After sending all tasks - Add single cleanup button
            cleanup_button = types.InlineKeyboardButton("🧹 Delete done items", callback_data="clear_done")
            markup_cleanup = types.InlineKeyboardMarkup()
            markup_cleanup.add(cleanup_button)

            bot.send_message(message.chat.id, "Actions:", reply_markup=markup_cleanup)

        except Exception as e:
            log.error(f"Redis read failed: {e}")
            bot.reply_to(message, "⚠️ Failed to read from Redis.")
        return

    # Otherwise, store the text to the shared default list
    try:
        # Split message into multiple lines
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        if not lines:
            bot.reply_to(message, "⚠️ No valid text to add.")
            return

        added_count = 0
        for line in lines:
            store_redis.add_shared_item(line, uid)
            added_count += 1

        # Reply summary
        if added_count == 1:
            bot.reply_to(message, "✅ Added 1 item to shared To-Do list")
        else:
            bot.reply_to(message, f"✅ Added {added_count} items to shared To-Do list")

    except Exception as e:
        log.error(f"Redis save failed: {e}")
        bot.reply_to(message, "⚠️ Failed to save to Redis.")

    bot.reply_to(message, "✏️ Saved item.")
    return

#endregion 


# region main 

@app.route(f"/{SECRET}", methods=["POST"])
def telegram_webhook():
    if request.headers.get("content-type") != "application/json":
        abort(403)
    update = telebot.types.Update.de_json(request.get_data(as_text=True))
    bot.process_new_updates([update])
    return "OK", 200

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




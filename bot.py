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

# --- Logging  ---
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
        deleted = store_redis.clear_messages(uid)
        bot.reply_to(
            message,
            f"Cleared {deleted} saved messages."
            if deleted > 0 else "Nothing to clear."
        )
        log.info(f"User {uid} cleared {deleted} messages from Redis")
    except Exception as e:
        log.error(f"Redis clear failed: {e}")
        bot.reply_to(message, "⚠️ Failed to clear messages from Redis.")


#---ON TEXT + ? 
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
            items = store_redis.get_messages(uid)
            if not items:
                bot.reply_to(message, "No messages stored in Redis.")
                return
            formatted = "\n".join(f"• {t}" for t in items if t)
            # Telegram message limit safeguard
            if len(formatted) > 3800:
                formatted = formatted[:3797] + "..."
            bot.reply_to(message, formatted)
        except Exception as e:
            log.error(f"Redis read failed: {e}")
            bot.reply_to(message, "⚠️ Failed to read from Redis.")
        return

    # Otherwise, store the text
    try:
        store_redis.save_message(uid, text)
        log.info(f"Saved text for user {uid}: {text}")
    except Exception as e:
        log.error(f"Redis save failed: {e}")

    bot.reply_to(message, "HELLOW WORLD")
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




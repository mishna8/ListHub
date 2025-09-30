# bot.py — Shared list (2 users), JSON + GitHub Gist persistence, Israel timezone
# Notes:
# - Does NOT drop pending Telegram updates on wake (good for Render Free sleep)
# - Saves data to a local JSON file (ephemeral) AND to a private GitHub Gist (persistent)
# - ENV required: BOT_TOKEN, GITHUB_TOKEN (classic PAT with 'gist' scope). Optional: GIST_ID, GIST_FILENAME, GIST_DESCRIPTION, DATA_PATH.

import os, re, json, threading, requests
from datetime import datetime
from zoneinfo import ZoneInfo
import time
from typing import Optional
from io import BytesIO
import telebot
from telebot import formatting
from telebot.types import Message
import logging

# --- Logging (נוח לדיבוג ברנדר) ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("hello-bot")

# --- Env vars ---
#the token is env on render
#BOT_TOKEN = "8468655841:AAEFFgX96L50KuL4BvNECI_Reuoq8YYOYWQ" 
BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip().strip('"').strip("'")
if not re.match(r"^\d+:[A-Za-z0-9_-]+$", BOT_TOKEN):
    raise RuntimeError("BOT_TOKEN is missing or malformed.")

# ---- ALLOW LIST ----
ALLOWED = {1317349810, 816672824}

def allowed(user_id: int) -> bool:
    return user_id in ALLOWED




# --- Bot ---
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

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
def on_text(message: Message):
    uid = message.from_user.id
    log.info(f"text from uid={uid}, text={message.text!r}")
    if not allowed(uid):
        bot.reply_to(message, "❌ לא מורשה להשתמש בבוט הזה")
    bot.send_chat_action(message.chat.id, "typing")
    bot.reply_to(message, "HELLOW WORLD")

#--MAIN FUNC
def run_polling():
    """
    Polling שמחזיק אחרי שינה של Render:
    - לא מוחקים pending updates (skip_pending=False)
    - webhook מבוטל מראש (remove_webhook)
    - timeout סביר כדי שלא להיתקע יותר מדי זמן
    - לולאות ניסיון כדי להתאושש מניתוקי רשת קצרים
    """
    # cancel all webhooks if we had any
    try:
        bot.remove_webhook()
    except Exception as e:
        log.warning(f"remove_webhook failed: {e}")

    # pull any percistent data from (JSON/Gist/Redis)
    # render will flush when redeploy
    # try:
    #     load_store()
    # except Exception as e:
    #     log.warning(f"load_store failed: {e}")

    log.info("Starting bot... (Ctrl+C to stop)")
    while True:
        try:
            # skip_pending=False => Collecting message queue after sleep
            # long_polling_timeout - Short, to release connection from time to time
            bot.infinity_polling(
                skip_pending=False,
                timeout=20,
                long_polling_timeout=20,
                logger_level=logging.INFO,
            )
        except KeyboardInterrupt:
            log.info("Shutting down by KeyboardInterrupt")
            break
        except Exception as e:
            # אם נפלה תקלה זמנית ברשת/CPU — נחכה מעט ונחזור לפולינג
            log.error(f"Polling error: {e}. Retrying in 3s...")
            time.sleep(3)

if __name__ == "__main__":
    run_polling()
   
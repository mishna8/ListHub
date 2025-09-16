# pip install pyTelegramBotAPI
import os
import telebot

BOT_TOKEN = "8468655841:AAEFFgX96L50KuL4BvNECI_Reuoq8YYOYWQ" # os.getenv("BOT_TOKEN") or "PASTE_YOUR_TOKEN"
bot = telebot.TeleBot(BOT_TOKEN)

# הרשימה של ה-IDs המורשים בלבד:
ALLOWED = {1317349810}  # שימי כאן את המספרים האמיתיים

def allowed(user_id: int) -> bool:
    return user_id in ALLOWED

@bot.message_handler(commands=['start'])
def start(m):
    if not allowed(m.from_user.id):
        return bot.reply_to(m, "הבוט פרטי. אין לך הרשאה.")
    bot.reply_to(m, f"היי {m.from_user.first_name}! את/ה ברשימת ההרשאות ✅")

#@bot.message_handler(func=lambda m: True)
#def handle(m):
#    if not allowed(m.from_user.id):
#        return  # מתעלמים בשקט או עונים הודעת סירוב
#    bot.reply_to(m, f"הד: {m.text}")

#bot.infinity_polling()

@bot.message_handler(content_types=['text'])
def on_text(m):
    bot.reply_to(m, "HELLOWORD")

if __name__ == "__main__":
    bot.infinity_polling()  # מריץ polling עד שסוגרים את החלון

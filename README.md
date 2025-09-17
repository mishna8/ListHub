No problem at all 🙂 Here’s your **README.md** rewritten in English:

---

````markdown
# Telegram To-Do Bot ✅

A personal Telegram bot for managing To-Do lists.  
Supports adding tasks, viewing all tasks, deleting by index, saving creation dates, and restricting access to specific user IDs.

## ✨ Features
- Add tasks by simply sending text (single line or multiple lines).
- View all tasks using `?`.
- Delete a task by its index (`-2` deletes the second task).
- Each task stores its creation date (UTC).
- Access control via an `ALLOWED` list of Telegram user IDs.
- Local persistence using `data.json`.

## 📦 Local Installation
1. Clone the repo:
   ```bash
   git clone https://github.com/<username>/<repo>.git
   cd <repo>
````

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Save your Bot Token as an environment variable (recommended) or directly in the code:

   ```bash
   # Windows CMD
   set BOT_TOKEN=123456:ABC-DEF...

   # Linux/Mac
   export BOT_TOKEN=123456:ABC-DEF...
   ```

4. Run the bot:

   ```bash
   python bot.py
   ```

5. Open the chat with your bot in Telegram (from the BotFather link), send `/start`, and you’re ready ✨

## 🚀 Deploying to Render

1. Push your bot code to GitHub, with:

   * `bot.py`
   * `requirements.txt`

2. Go to [Render](https://dashboard.render.com/) → **New +** → **Web Service**.

3. Select your GitHub repo.

4. Configure:

   * **Build Command**:

     ```bash
     pip install -r requirements.txt
     ```
   * **Start Command**:

     ```bash
     python bot.py
     ```
   * **Instance Type**: Free

5. Under **Settings → Environment**, add:

   * `BOT_TOKEN = <your BotFather token>`

6. Deploy → Check logs for `Starting bot...`.

## 💤 Keep the Bot Awake

On Render Free Plan, services sleep after \~15 minutes of inactivity.
To keep the bot always awake, use [UptimeRobot](https://uptimerobot.com/) or [cron-job.org](https://cron-job.org/) to ping your service every \~14 minutes (or only during daytime hours).

## ⚙️ Optional Environment Variables

* `APP_ENV` — mark environment (`prod` / `dev`).
* `ENFORCE_ALLOWLIST` — force allowlist checks on user IDs.

## 🛡️ Notes

* Tasks are stored in `data.json` locally. On Render, this file is **not persistent** across restarts → for production you should use Redis or another database.
* Dates are stored in ISO UTC format.

---

👩‍💻 Built with Python + [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI)

```

---

👉 Do you want me to also add a short section explaining **how to get your Telegram user ID** so you can add it to the `ALLOWED` list?
```

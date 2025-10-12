

# Telegram To-Do Bot

A personal Telegram bot for managing To-Do lists for allowed users via user IDs.  

## Features

- Access control via an `ALLOWED` list of Telegram user IDs.(to get your telegram id text /start to @userinfobot)
- Add tasks `on text` (single line or multiple lines).
- `/Del` command to delete tasks on _____
- `/List` or `?` command to view all items on list.
- `/Clear` command to delete all items on list.
- `coming soon` - reminders and nudges
- `coming soon` - Tasks can have statuses (`/Done` command), deadlines and tags, can be filltered

## Stack
- **Python 3.11+**
- **Flask** – webhook endpoint for Render
- **pyTelegramBotAPI** – Telegram Bot API wrapper
(https://github.com/eternnoir/pyTelegramBotAPI)
- **Upstash Redis** – persistent storage (serverless, free tier supported)
(https://console.upstash.com/redis/240ced7c-278c-44c1-84f5-ebebc672f6cd/details?teamid=0)
- **Render.com** – hosting + auto-redeploy on push
(https://dashboard.render.com/web/srv-d35h5vje5dus73ei3ohg/deploys/dep-d3inedripnbc73eauns0?r=2025-10-07%4020%3A24%3A28%7E2025-10-07%4020%3A29%3A06)

## Render free plan Shortcomings

* On Render Free Plan, services sleep after \~15 minutes of inactivity.
`COMING SOON` - feature to keep the bot always awake for no delay
* On Render, memory is **not persistent** across restarts/redeployments, using Redis as DB

##  Environment Variables

| Key | Description |
|-----|--------------|
| `BOT_TOKEN` | Your Telegram Bot token from [@BotFather](https://t.me/BotFather) |
| `UPSTASH_REDIS_REST_URL` | Redis REST endpoint from Upstash |
| `UPSTASH_REDIS_REST_TOKEN` | Redis REST token from Upstash |
| `REDIS_PREFIX` *(optional)* | Key prefix (default: `tb`) |
| `APP_URL` | the Render service URL for the webhook URL |
| `WEBHOOK_SECRET` | Custom string for securing your Flask webhook URL |

## Local Installation
1. Clone the repo:
   ```bash
   git clone https://github.com/<username>/<repo>.git
   cd <repo>
   ```

2. run:

   ```bash
   pip install -r requirements.txt #Install dependencies
   python bot.py #Run the bot
   ```

3. Open the chat with your bot in Telegram (from the BotFather link), send `/start`



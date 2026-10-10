# Telegram Crypto Price Bot

A Telegram bot that shows live crypto prices in EUR and automatically messages you when a coin hits your price target.

## Features

| Command | What it does |
|---|---|
| `/start` | Show help |
| `/price <coin>` | Current price in EUR, e.g. `/price solana` |
| `/alert <coin> <price>` | Notify when the price hits a target, e.g. `/alert solana 150` |
| `/alerts` | List your active alerts |
| `/stopalerts` | Remove all your alerts |

- Automatically detects whether you're waiting for a rise or a drop
- Checks all alerts every 30 seconds in a single API request
- Handles meme coins priced at fractions of a cent
- Clear error messages for unknown coins, typos or an unavailable price source
- The bot token is never stored in code or shown in logs

## Setup

```
pip install -r requirements.txt
```

Create a bot with [@BotFather](https://t.me/BotFather) and set the token as an environment variable:

```
# Windows (PowerShell)
$env:TELEGRAM_TOKEN="your_token"
python pricebot.py
```

```
# Mac/Linux
export TELEGRAM_TOKEN="your_token"
python pricebot.py
```

## Tech

- Python 3.10+
- [python-telegram-bot](https://python-telegram-bot.org/) (async)
- Price data from the [CoinGecko API](https://www.coingecko.com/en/api)

## Custom bots

Need a bot for your Telegram group or Discord server? Price alerts, welcome messages, moderation, or integrations with your shop or tools. Get in touch via GitHub.

**Order a custom Telegram group bot on Fiverr:** https://www.fiverr.com/s/RVVE0DL

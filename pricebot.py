"""
Telegram Crypto Price Bot
Commands:
  /start                 - help
  /price <coin>          - current price in EUR (e.g. /price solana)
  /alert <coin> <price>  - notify when the price hits a target (e.g. /alert solana 150)
  /alerts                - list your active alerts
  /stopalerts            - remove all your alerts
"""

import asyncio
import logging
import os

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ["TELEGRAM_TOKEN"]  # from @BotFather - never put it in code or on GitHub
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
CHECK_INTERVAL = 30  # seconds between price checks

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # keeps the token out of the logs
log = logging.getLogger(__name__)

# Active alerts: {"chat_id", "coin", "target", "direction"}
# Stored in memory, so they are lost on restart
alerts: list[dict] = []


async def fetch_prices(coins: set[str]) -> dict[str, float]:
    """Fetch EUR prices for several coins in a single request."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(COINGECKO_URL, params={"ids": ",".join(coins), "vs_currencies": "eur"})
        r.raise_for_status()
        data = r.json()
    return {coin: info["eur"] for coin, info in data.items() if "eur" in info}


async def fetch_price(coin: str) -> float | None:
    return (await fetch_prices({coin})).get(coin)


def fmt(price: float) -> str:
    # Meme coins often trade at fractions of a cent, so show more decimals
    return f"€{price:,.2f}" if price >= 1 else f"€{price:.8f}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I track crypto prices and send alerts.\n\n"
        "/price <coin> - current price\n"
        "/alert <coin> <price> - get notified at a price target\n"
        "/alerts - your active alerts\n"
        "/stopalerts - remove all alerts\n\n"
        "Example: /alert solana 150"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /price <coin>, e.g. /price solana")
        return

    coin = context.args[0].lower()
    try:
        p = await fetch_price(coin)
    except httpx.HTTPError:
        await update.message.reply_text("Price source is unavailable right now, please try again shortly.")
        return

    if p is None:
        await update.message.reply_text(
            f"'{coin}' not found. Use the CoinGecko id, e.g. bitcoin, ethereum, solana."
        )
    else:
        await update.message.reply_text(f"{coin.capitalize()}: {fmt(p)}")


async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /alert <coin> <price>, e.g. /alert solana 150")
        return

    coin = context.args[0].lower()
    try:
        target = float(context.args[1].replace(",", "."))  # accepts 150,5 and 150.5
    except ValueError:
        await update.message.reply_text("That's not a valid price. Example: /alert solana 150")
        return

    try:
        current = await fetch_price(coin)
    except httpx.HTTPError:
        await update.message.reply_text("Price source is unavailable right now, please try again shortly.")
        return

    if current is None:
        await update.message.reply_text(f"'{coin}' not found. Try e.g. bitcoin or solana.")
        return

    # Target above current price -> wait for a rise, otherwise wait for a drop
    direction = "above" if target > current else "below"
    alerts.append({"chat_id": update.effective_chat.id, "coin": coin, "target": target, "direction": direction})

    verb = "rises to" if direction == "above" else "drops to"
    await update.message.reply_text(
        f"Alert set: I'll message you when {coin} {verb} {fmt(target)}.\n"
        f"Now: {fmt(current)}"
    )


async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    own = [a for a in alerts if a["chat_id"] == update.effective_chat.id]
    if not own:
        await update.message.reply_text("You have no active alerts.")
        return

    lines = [
        f"{i}. {a['coin']} {'≥' if a['direction'] == 'above' else '≤'} {fmt(a['target'])}"
        for i, a in enumerate(own, start=1)
    ]
    await update.message.reply_text("Your alerts:\n" + "\n".join(lines))


async def stop_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    count = sum(1 for a in alerts if a["chat_id"] == chat_id)
    alerts[:] = [a for a in alerts if a["chat_id"] != chat_id]
    await update.message.reply_text(f"{count} alert(s) removed.")


async def check_alerts(app: Application) -> None:
    """Runs in the background and checks all alerts every CHECK_INTERVAL seconds."""
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        if not alerts:
            continue
        try:
            prices = await fetch_prices({a["coin"] for a in alerts})
        except httpx.HTTPError as e:
            log.warning("Fetching prices failed: %s", e)
            continue

        for a in list(alerts):
            p = prices.get(a["coin"])
            if p is None:
                continue
            hit = p >= a["target"] if a["direction"] == "above" else p <= a["target"]
            if hit:
                alerts.remove(a)
                try:
                    await app.bot.send_message(
                        a["chat_id"],
                        f"🚨 {a['coin'].capitalize()} is now at {fmt(p)} "
                        f"(your target was {fmt(a['target'])})",
                    )
                except Exception as e:  # e.g. the user blocked the bot
                    log.warning("Sending message failed: %s", e)


async def post_init(app: Application) -> None:
    # Start the background task; keep a reference so it isn't garbage collected
    app.bot_data["checker"] = asyncio.create_task(check_alerts(app))


def main() -> None:
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("alert", alert))
    app.add_handler(CommandHandler("alerts", list_alerts))
    app.add_handler(CommandHandler("stopalerts", stop_alerts))
    app.run_polling()


if __name__ == "__main__":
    main()

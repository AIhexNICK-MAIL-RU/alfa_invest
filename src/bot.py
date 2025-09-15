import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


# Minimal ASGI app for deployment platforms expecting `src.bot:app`
app = FastAPI(title="TG Style Bot")


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "message": "Telegram style bot server"}


@app.get("/healthz")
async def healthcheck() -> dict:
    return {"status": "healthy"}


# Telegram Bot integration for Render webhook
logger = logging.getLogger(__name__)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

_bot_app: Application | None = None


def get_bot_app() -> Application:
    global _bot_app
    if _bot_app is None:
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        _bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        async def cmd_start(update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "Привет! Пришли текст — верну стилизованную версию с хэштегом."
            )

        async def on_text(update, context: ContextTypes.DEFAULT_TYPE):
            text = (update.message.text or "").strip()
            # TODO: вставить стилизацию текста и хэштеги
            await update.message.reply_text(f"{text}\n\n#альфаиндекс")

        _bot_app.add_handler(CommandHandler("start", cmd_start))
        _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return _bot_app


@app.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    bot_app = get_bot_app()
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}


@app.on_event("startup")
async def on_startup() -> None:
    # Auto set webhook on Render using RENDER_EXTERNAL_URL
    external_url = os.getenv("RENDER_EXTERNAL_URL")
    if not external_url:
        logger.info("RENDER_EXTERNAL_URL is not set; skipping webhook setup")
        return
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set; skipping webhook setup")
        return
    webhook_url = external_url.rstrip("/") + "/webhook"
    bot_app = get_bot_app()
    await bot_app.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")


if __name__ == "__main__":
    # Optional local run for debugging
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("src.bot:app", host="0.0.0.0", port=port, reload=False)



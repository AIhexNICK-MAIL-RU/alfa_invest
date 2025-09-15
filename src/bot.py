import os
import logging
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import random
from pathlib import Path

from .storage import JsonKVStore
from .style_profile import StyleProfile


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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_bot_app: Application | None = None


def get_bot_app() -> Application:
    global _bot_app
    if _bot_app is None:
        if not TELEGRAM_BOT_TOKEN:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
        _bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        async def cmd_start(update, context: ContextTypes.DEFAULT_TYPE):
            if update.message:
                await update.message.reply_text(
                    "Привет! Пришли текст — верну стилизованную версию с хэштегом."
                )

        async def on_text(update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message:
                return
            text = (update.message.text or "").strip()
            styled = await rewrite_text_in_style(chat_id=str(update.effective_chat.id), input_text=text)
            await update.message.reply_text(styled)

        async def on_channel_text(update, context: ContextTypes.DEFAULT_TYPE):
            if not update.channel_post:
                return
            text = (update.channel_post.text or "").strip()
            styled = await rewrite_text_in_style(chat_id=str(update.effective_chat.id), input_text=text)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=styled)

        async def on_any(update, context: ContextTypes.DEFAULT_TYPE):
            try:
                msg = update.effective_message
                if not msg:
                    return
                text = (msg.text or msg.caption or "").strip()
                if not text:
                    return
                styled = await rewrite_text_in_style(chat_id=str(update.effective_chat.id), input_text=text)
                await msg.reply_text(styled)
            except Exception as e:
                logger.exception("handler failure: %s", e)

        _bot_app.add_handler(CommandHandler("start", cmd_start))
        _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
        _bot_app.add_handler(MessageHandler(filters.ChatType.CHANNEL & filters.TEXT, on_channel_text))
        _bot_app.add_handler(MessageHandler(filters.ALL, on_any))
        
        async def on_error(update, context: ContextTypes.DEFAULT_TYPE):
            logger.exception("Update caused error: %s", context.error)
        _bot_app.add_error_handler(on_error)
    return _bot_app


store = JsonKVStore(path=Path(".data/store.json"))


async def rewrite_text_in_style(chat_id: str, input_text: str) -> str:
    profile_dict = store.get(chat_id)
    if profile_dict is None:
        profile = StyleProfile.default()
    else:
        profile = StyleProfile(
            voice_instructions=profile_dict.get("voice_instructions", StyleProfile.default().voice_instructions),
            hashtags=profile_dict.get("hashtags", StyleProfile.default().hashtags),
        )

    hashtags = profile.hashtags or StyleProfile.default().hashtags
    chosen_tag = random.choice(hashtags)

    if not OPENAI_API_KEY:
        # Fallback: simple paraphrase stub
        return f"{input_text}\n\n{chosen_tag}"

    client = OpenAI(api_key=OPENAI_API_KEY)
    system_prompt = (
        "Ты редактор телеграм-канала по инвестициям. Перепиши текст в заданном тоне. "
        "Сохраняй факты, сокращай воду, повышай ясность, используй деловой стиль. "
        "Отвечай на русском. Не добавляй эмодзи."
    )
    user_prompt = (
        f"Тон и инструкция: {profile.voice_instructions}\n\n"
        f"Перепиши следующий текст в этом стиле. Верни только новый текст без пояснений.\n\n"
        f"Текст:\n{input_text}"
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=600,
    )
    rewritten = resp.choices[0].message.content.strip()
    return f"{rewritten}\n\n{chosen_tag}"

@app.post("/webhook")
async def telegram_webhook(request: Request) -> dict:
    bot_app = get_bot_app()
    data = await request.json()
    try:
        logger.info("/webhook received update: %s", data.get("update_id"))
    except Exception:
        logger.info("/webhook received payload")
    update = Update.de_json(data, bot_app.bot)
    # Process asynchronously to avoid Telegram 10s timeout
    import asyncio
    asyncio.create_task(bot_app.process_update(update))
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
    # Properly initialize/start PTB Application for webhook processing
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to: {webhook_url}")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if _bot_app is None:
        return
    try:
        await _bot_app.bot.delete_webhook()
    finally:
        await _bot_app.stop()
        await _bot_app.shutdown()


if __name__ == "__main__":
    # Optional local run for debugging
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("src.bot:app", host="0.0.0.0", port=port, reload=False)



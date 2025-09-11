# TG Style Bot

1) Create .env from .env.example and fill keys.
2) Activate venv: source .venv/bin/activate
3) Run bot polling: python -m src.bot
4) Or run webhook: uvicorn src.bot:app --host 0.0.0.0 --port 8000

Commands:
- /start — help
- /style <url> — set style by post URL
- send text — returns stylized text + hashtag
- /set_hashtags h1;h2 — override tag choices

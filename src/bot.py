import os
from fastapi import FastAPI


# Minimal ASGI app for deployment platforms expecting `src.bot:app`
app = FastAPI(title="TG Style Bot")


@app.get("/")
async def root() -> dict:
    return {"status": "ok", "message": "Telegram style bot server"}


@app.get("/healthz")
async def healthcheck() -> dict:
    return {"status": "healthy"}


if __name__ == "__main__":
    # Optional local run for debugging
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("src.bot:app", host="0.0.0.0", port=port, reload=False)



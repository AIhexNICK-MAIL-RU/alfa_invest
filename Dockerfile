FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \n    PIP_NO_CACHE_DIR=1 \n    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \n    build-essential curl && \n    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default to webhook server; override CMD for polling
EXPOSE 8000
CMD ["uvicorn", "src.bot:app", "--host", "0.0.0.0", "--port", "8000"]

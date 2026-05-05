FROM python:3.11-slim

# ffmpeg is required by faster-whisper and the av library for audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent volume for SQLite (mount /data on Railway to keep reminders between deploys)
RUN mkdir -p /data

ENV DB_PATH=/data/reminders.db

CMD ["python", "-m", "bot.main"]

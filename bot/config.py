import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# Railway injects RAILWAY_PUBLIC_DOMAIN automatically when a service has a public domain.
# If it is present, switch to webhook mode and build the webhook URL automatically.
_railway_domain: str = os.getenv("RAILWAY_PUBLIC_DOMAIN", "")

MODE: str = os.getenv("MODE", "webhook" if _railway_domain else "polling")
WEBHOOK_URL: str = os.getenv(
    "WEBHOOK_URL",
    f"https://{_railway_domain}" if _railway_domain else "",
)
# Railway exposes the service via the PORT env var; fall back to WEBHOOK_PORT for manual setups.
WEBHOOK_PORT: int = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "8443")))
WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")

WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "small")
DB_PATH: str = os.getenv("DB_PATH", "reminders.db")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required. Copy .env.example to .env and set BOT_TOKEN.")

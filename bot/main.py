"""
ReminderTelegramBot entry point.
Supports both polling (local dev) and webhook (server deploy) modes.
Set MODE=polling or MODE=webhook in .env
"""
from pathlib import Path
import sys

# Running `python bot/main.py` puts only .../bot on sys.path; repo root must be on path
# so `import bot.*` resolves. With `python -m bot.main`, __package__ is set and paths are OK.
if not __package__:
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import bot.config as config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

dp = Dispatcher()
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)


async def on_startup() -> None:
    logger.info("Starting ReminderTelegramBot (mode=%s)...", config.MODE)

    # Init database
    try:
        from bot.database.models import init_db
        await init_db(config.DB_PATH)
        logger.info("Database ready: %s", config.DB_PATH)
    except Exception as e:
        logger.error("Database init failed: %s", e)

    # Preload Whisper STT model in background thread — don't block polling startup
    try:
        from bot.services.stt import preload_model
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(loop.run_in_executor(None, preload_model))
        logger.info("Whisper model loading in background...")
    except Exception as e:
        logger.warning("Whisper preload skipped (ffmpeg missing?): %s", e)

    # Start scheduler and load pending reminders
    try:
        from bot.services.scheduler import start_scheduler, load_pending_reminders
        start_scheduler()
        await load_pending_reminders(bot, config.DB_PATH)
    except Exception as e:
        logger.error("Scheduler init failed: %s", e)

    # Register webhook if in webhook mode
    if config.MODE == "webhook":
        webhook_url = f"{config.WEBHOOK_URL}/webhook"
        await bot.set_webhook(
            url=webhook_url,
            secret_token=config.WEBHOOK_SECRET or None,
        )
        logger.info("Webhook set: %s", webhook_url)


async def on_shutdown() -> None:
    logger.info("Shutting down...")
    try:
        from bot.services.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    if config.MODE == "webhook":
        try:
            await bot.delete_webhook()
        except Exception:
            pass


def _register_routers() -> None:
    """Register all handler routers on the dispatcher."""
    from bot.handlers.start import router as start_router
    dp.include_router(start_router)

    try:
        from bot.handlers.timezone import router as tz_router
        dp.include_router(tz_router)
    except ImportError as e:
        logger.warning("Timezone handler not available: %s", e)

    try:
        from bot.handlers.voice import router as voice_router
        dp.include_router(voice_router)
    except ImportError as e:
        logger.warning("Voice handler not available: %s", e)

    try:
        from bot.handlers.text import router as text_router
        dp.include_router(text_router)
    except ImportError as e:
        logger.warning("Text handler not available: %s", e)


def run_polling() -> None:
    """Run bot in long-polling mode (for local development)."""
    async def _polling():
        _register_routers()
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    asyncio.run(_polling())


def run_webhook() -> None:
    """Run bot in webhook mode (for server deployment)."""
    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    async def _startup(app: web.Application) -> None:
        await on_startup()

    async def _shutdown(app: web.Application) -> None:
        await on_shutdown()

    _register_routers()

    app = web.Application()
    app.on_startup.append(_startup)
    app.on_shutdown.append(_shutdown)

    handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=config.WEBHOOK_SECRET or None,
    )
    handler.register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    logger.info("Starting webhook server on port %d", config.WEBHOOK_PORT)
    web.run_app(app, host="0.0.0.0", port=config.WEBHOOK_PORT)


if __name__ == "__main__":
    if config.MODE == "webhook":
        run_webhook()
    else:
        run_polling()

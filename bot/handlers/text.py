"""
Handler for text-based reminder messages.
Users can type reminders directly without voice.
"""
import logging

from aiogram import F, Router, types

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_reminder(message: types.Message) -> None:
    """Handle plain text messages as reminder requests."""
    text = message.text.strip()
    if not text:
        return

    logger.info("Text reminder from user %d: %s", message.from_user.id, text)

    from bot.handlers.voice import _process_reminder_from_text
    await _process_reminder_from_text(message, text)

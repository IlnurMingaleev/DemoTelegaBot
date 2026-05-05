"""
Handler for Telegram voice messages.
Pipeline: download OGG → STT transcription → NLP date extraction → save reminder.
"""
import logging
from aiogram import Router, F, types, Bot

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot) -> None:
    """Handle incoming voice messages."""
    # Send "typing..." indicator for long STT processing
    await bot.send_chat_action(message.chat.id, "typing")

    # Download voice file bytes
    try:
        file = await bot.get_file(message.voice.file_id)
        ogg_bytes = await bot.download_file(file.file_path)
        if hasattr(ogg_bytes, 'read'):
            ogg_bytes = ogg_bytes.read()
    except Exception as e:
        logger.error("Failed to download voice file: %s", e)
        await message.answer("❌ Не удалось загрузить голосовое сообщение. Попробуйте ещё раз.")
        return

    # Transcribe voice to text
    try:
        from bot.services.stt import transcribe_ogg
        text = await transcribe_ogg(ogg_bytes)
    except Exception as e:
        logger.error("STT service error: %s", e)
        await message.answer(
            "❌ Ошибка сервиса распознавания речи.\n"
            "Убедитесь, что ffmpeg установлен. Попробуйте отправить текстовое сообщение."
        )
        return

    if not text:
        await message.answer(
            "❌ Не удалось распознать голосовое сообщение.\n"
            "Попробуйте говорить чётче или отправьте текстовое напоминание."
        )
        return

    logger.info("Voice transcript from user %d: %s", message.from_user.id, text)

    # Pass transcribed text to NLP reminder processor
    await _process_reminder_from_text(message, text, raw_transcript=text)


async def _process_reminder_from_text(
    message: types.Message,
    text: str,
    raw_transcript: str = "",
) -> None:
    """Common logic for processing reminder text (used by voice and text handlers)."""
    import bot.config as config

    try:
        from bot.services.nlp import process_reminder_text
        parsed = await process_reminder_text(
            text=text,
            user_id=message.from_user.id,
            db_path=config.DB_PATH,
        )
    except Exception as e:
        logger.error("NLP processing error: %s", e)
        await message.answer("❌ Ошибка обработки сообщения. Попробуйте позже.")
        return

    if parsed is None:
        await message.answer(
            "❓ Не смог найти дату/время в сообщении.\n\n"
            "Попробуйте:\n"
            "• «Завтра в 15:00 — встреча»\n"
            "• «Через 2 часа позвонить маме»\n"
            "• «15 мая в 10 утра сдать отчёт»"
        )
        return

    # Save reminder to DB
    try:
        from bot.database.models import add_reminder, get_user_timezone
        from bot.services.scheduler import schedule_reminder
        from bot.services.nlp import format_confirmation

        tz_name = await get_user_timezone(config.DB_PATH, message.from_user.id)

        # Warn if user hasn't set their timezone yet
        if tz_name == "UTC":
            await message.answer(
                "⚠️ <b>Часовой пояс не установлен!</b>\n\n"
                "Сейчас используется UTC. Чтобы напоминания приходили "
                "в правильное время — установите свой часовой пояс:\n"
                "/timezone"
            )

        reminder_id = await add_reminder(
            db_path=config.DB_PATH,
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            remind_at=parsed.remind_at,
            text=parsed.text,
            raw=raw_transcript,
        )

        schedule_reminder(
            bot=message.bot,
            reminder_id=reminder_id,
            chat_id=message.chat.id,
            text=parsed.text,
            remind_at=parsed.remind_at,
            db_path=config.DB_PATH,
        )

        confirmation = format_confirmation(parsed.remind_at, parsed.text, tz_name)
        await message.answer(confirmation)

    except Exception as e:
        logger.error("Failed to save/schedule reminder: %s", e)
        await message.answer("❌ Не удалось сохранить напоминание. Попробуйте ещё раз.")

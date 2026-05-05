from aiogram import Router, types
from aiogram.filters import Command, CommandObject
import logging

import bot.config as config

router = Router()
logger = logging.getLogger(__name__)

WELCOME_TEXT = """
👋 <b>Привет! Я бот-напоминалка.</b>

Я умею принимать голосовые и текстовые сообщения с датой и временем, и напоминать вам в нужный момент.

<b>Примеры фраз:</b>
• «Напомни мне завтра в 15:00 про встречу»
• «Через 2 часа позвонить маме»
• «15 мая в 10 утра сдать отчёт»
• «В пятницу в 18:00 купить продукты»

<b>Команды:</b>
/timezone — установить часовой пояс
/list — список активных напоминаний
/delete — удалить напоминание
/help — подробная справка

━━━━━━━━━━━━━━━━━━
⚠️ <b>Первый шаг — установите часовой пояс:</b>

👉 /timezone

Без этого напоминания будут приходить по UTC, а не по вашему местному времени!
"""

HELP_TEXT = """
<b>📖 Справка по боту</b>

<b>Форматы напоминаний (голос или текст):</b>
• Завтра в 15:00 — встреча
• Через 2 часа — позвонить
• Через 30 минут — выключить плиту
• 15 мая в 10 утра — сдать отчёт
• В пятницу в 18:00 — купить продукты
• Сегодня в 20:00 — принять таблетку

<b>Команды:</b>
/start — начать работу
/help — эта справка
/timezone — установить часовой пояс
/list — активные напоминания
/delete [id] — удалить напоминание
"""


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    await message.answer(WELCOME_TEXT)


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("list"))
async def cmd_list(message: types.Message) -> None:
    try:
        from bot.database.models import get_user_reminders, get_user_timezone
        reminders = await get_user_reminders(config.DB_PATH, message.from_user.id)
        if not reminders:
            await message.answer("📭 Нет активных напоминаний.")
            return

        lines = ["📋 <b>Активные напоминания:</b>\n"]
        import pytz
        from datetime import datetime

        tz_name = await get_user_timezone(config.DB_PATH, message.from_user.id)
        tz = pytz.timezone(tz_name)

        for r in reminders:
            dt = datetime.fromisoformat(r["remind_at"]).astimezone(tz)
            lines.append(
                f"🔔 <b>#{r['id']}</b> — {dt.strftime('%d.%m.%Y %H:%M')} ({tz_name})\n"
                f"   📝 {r['text']}\n"
            )
        lines.append("\nЧтобы удалить: /delete [id]")
        await message.answer("\n".join(lines))
    except Exception as e:
        logger.error("Error in /list: %s", e)
        await message.answer("❌ Ошибка при получении списка напоминаний.")


@router.message(Command("delete"))
async def cmd_delete(message: types.Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer(
            "Укажите ID напоминания: /delete 5\n"
            "Посмотреть список: /list"
        )
        return

    try:
        reminder_id = int(command.args.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом. Например: /delete 5")
        return

    try:
        from bot.database.models import delete_reminder
        from bot.services.scheduler import cancel_reminder
        deleted = await delete_reminder(config.DB_PATH, reminder_id, message.from_user.id)
        if deleted:
            cancel_reminder(reminder_id)
            await message.answer(f"✅ Напоминание #{reminder_id} удалено.")
        else:
            await message.answer(f"❌ Напоминание #{reminder_id} не найдено или уже удалено.")
    except Exception as e:
        logger.error("Error in /delete: %s", e)
        await message.answer("❌ Ошибка при удалении напоминания.")

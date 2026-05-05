"""
Handler for /timezone command — lets users set their timezone via inline keyboard or text input.
"""
import logging
from datetime import datetime

import pytz
from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()
logger = logging.getLogger(__name__)

COMMON_TIMEZONES = [
    ("🇷🇺 Москва (UTC+3)", "Europe/Moscow"),
    ("🇷🇺 Самара (UTC+4)", "Europe/Samara"),
    ("🇷🇺 Екатеринбург (UTC+5)", "Asia/Yekaterinburg"),
    ("🇷🇺 Омск (UTC+6)", "Asia/Omsk"),
    ("🇷🇺 Красноярск (UTC+7)", "Asia/Krasnoyarsk"),
    ("🇷🇺 Иркутск (UTC+8)", "Asia/Irkutsk"),
    ("🇷🇺 Якутск (UTC+9)", "Asia/Yakutsk"),
    ("🇷🇺 Владивосток (UTC+10)", "Asia/Vladivostok"),
    ("🇷🇺 Магадан (UTC+11)", "Asia/Magadan"),
    ("🇷🇺 Камчатка (UTC+12)", "Asia/Kamchatka"),
    ("🇺🇦 Киев (UTC+2/3)", "Europe/Kiev"),
    ("🇧🇾 Минск (UTC+3)", "Europe/Minsk"),
    ("🇰🇿 Алматы (UTC+5)", "Asia/Almaty"),
    ("🌍 UTC", "UTC"),
]


class TimezoneForm(StatesGroup):
    waiting_for_manual_tz = State()


def _build_tz_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"tz:{tz_id}")]
        for label, tz_id in COMMON_TIMEZONES
    ]
    buttons.append([InlineKeyboardButton(text="✏️ Ввести вручную", callback_data="tz:manual")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _current_offset_str(tz: pytz.BaseTzInfo) -> str:
    """Return current UTC offset string like UTC+3."""
    now = datetime.now(tz)
    offset = now.strftime("%z")
    if len(offset) >= 5:
        sign = offset[0]
        hours = int(offset[1:3])
        minutes = int(offset[3:5])
        if minutes == 0:
            return f"UTC{sign}{hours}"
        return f"UTC{sign}{hours}:{minutes:02d}"
    return "UTC"


@router.message(Command("timezone"))
async def cmd_timezone(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🌍 <b>Выберите ваш часовой пояс:</b>\n\n"
        "Это необходимо для точного планирования напоминаний.",
        reply_markup=_build_tz_keyboard(),
    )


@router.callback_query(F.data.startswith("tz:"))
async def handle_tz_callback(callback: types.CallbackQuery, state: FSMContext) -> None:
    tz_value = callback.data[3:]

    if tz_value == "manual":
        await state.set_state(TimezoneForm.waiting_for_manual_tz)
        await callback.message.edit_text(
            "✏️ Введите часовой пояс в формате <code>Continent/City</code>\n\n"
            "Примеры: <code>Europe/Moscow</code>, <code>America/New_York</code>, <code>Asia/Tokyo</code>\n\n"
            "Полный список: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        )
        await callback.answer()
        return

    await _save_timezone(callback.message, callback.from_user.id, tz_value, edit=True)
    await callback.answer()


@router.message(TimezoneForm.waiting_for_manual_tz)
async def handle_manual_tz(message: types.Message, state: FSMContext) -> None:
    tz_input = message.text.strip()
    try:
        pytz.timezone(tz_input)
    except pytz.exceptions.UnknownTimeZoneError:
        await message.answer(
            f"❌ Неизвестный часовой пояс: <code>{tz_input}</code>\n\n"
            "Проверьте написание. Пример: <code>Europe/Moscow</code>\n"
            "Попробуйте снова или выберите из списка: /timezone"
        )
        return

    await state.clear()
    await _save_timezone(message, message.from_user.id, tz_input, edit=False)


async def _save_timezone(
    message: types.Message,
    user_id: int,
    timezone: str,
    edit: bool = False,
) -> None:
    import bot.config as config
    from bot.database.models import set_user_timezone

    try:
        await set_user_timezone(config.DB_PATH, user_id, timezone)
    except Exception as e:
        logger.error("Failed to save timezone for user %d: %s", user_id, e)
        text = "❌ Не удалось сохранить часовой пояс. Попробуйте позже."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    tz = pytz.timezone(timezone)
    offset = _current_offset_str(tz)
    confirm_text = (
        f"✅ <b>Часовой пояс установлен!</b>\n\n"
        f"🌍 {timezone} ({offset})\n\n"
        f"Теперь можете отправлять голосовые или текстовые напоминания."
    )
    if edit:
        await message.edit_text(confirm_text)
    else:
        await message.answer(confirm_text)

    logger.info("User %d set timezone to %s", user_id, timezone)

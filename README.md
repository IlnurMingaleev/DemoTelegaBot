# 🔔 ReminderTelegramBot

Telegram-бот с голосовыми и текстовыми напоминаниями. Использует бесплатное offline распознавание речи (Whisper AI) без платных API.

**A Telegram reminder bot with voice and text support. Uses free offline speech recognition (Whisper AI) — no paid APIs.**

---

## 📋 Возможности / Features

- 🎤 Голосовые напоминания — просто скажите когда и о чём
- 💬 Текстовые напоминания — напишите в свободной форме
- 🌍 Поддержка часовых поясов
- 🔔 Уведомления в точное время
- 📋 Список и удаление напоминаний
- 🚀 Два режима: polling (локально) и webhook (сервер)

---

## ⚡ Быстрый старт / Quick Start

### Шаг 1: Получить токен бота / Get Bot Token

1. Откройте Telegram и найдите **@BotFather**
2. Отправьте команду `/newbot`
3. Следуйте инструкциям: введите имя и username бота
4. Скопируйте полученный **токен** (вида `123456:ABC-DEF...`)

### Шаг 2: Установить зависимости / Install Dependencies

**Требования / Requirements:**
- Python 3.11+
- Git
- ffmpeg (обязательно для голосовых сообщений!)

**Установка ffmpeg / Install ffmpeg:**

```bash
# Windows (через winget):
winget install ffmpeg

# Windows (через Chocolatey):
choco install ffmpeg

# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# macOS:
brew install ffmpeg
```

**Установка Python пакетов / Install Python packages:**

```bash
git clone https://github.com/yourusername/ReminderTelegramBot.git
cd ReminderTelegramBot
pip install -r requirements.txt
```

### Шаг 3: Настроить конфигурацию / Configure

```bash
# Скопировать шаблон / Copy template
cp .env.example .env   # Linux/macOS
copy .env.example .env  # Windows
```

Откройте `.env` и заполните:

```env
BOT_TOKEN=123456:ABC-DEF...  # Ваш токен от @BotFather
MODE=polling                  # polling для локального запуска
```

### Шаг 4: Запустить бота / Run the Bot

Из корня репозитория / From the repo root:

```bash
python -m bot.main
```

Также можно / You can also run:

```bash
python bot/main.py
```

### Шаг 5: Настроить часовой пояс / Set Timezone

Откройте вашего бота в Telegram и отправьте `/timezone` — выберите ваш часовой пояс из списка.

---

## 🎤 Форматы напоминаний / Reminder Formats

Отправьте **голосовое** или **текстовое** сообщение в любом из форматов:

| Фраза | Когда сработает |
|-------|----------------|
| `Напомни мне завтра в 15:00 про встречу` | Завтра в 15:00 |
| `Через 2 часа позвонить маме` | +2 часа от сейчас |
| `Через 30 минут выключить плиту` | +30 минут |
| `15 мая в 10 утра — сдать отчёт` | 15 мая, 10:00 |
| `В пятницу в 18:00 купить продукты` | В ближайшую пятницу |
| `Сегодня в 20:00 принять таблетку` | Сегодня в 20:00 |

После установки напоминания бот пришлёт подтверждение:

```
✅ Напоминание установлено!

📅 Дата: 15 мая 2026
🕒 Время: 10:00
🌍 Часовой пояс: Europe/Moscow (UTC+3)
📝 Текст: сдать отчёт
```

---

## 🤖 Команды бота / Bot Commands

| Команда | Описание |
|---------|----------|
| `/start` | Запустить бота, приветственное сообщение |
| `/help` | Справка по форматам напоминаний |
| `/timezone` | Установить часовой пояс |
| `/list` | Список активных напоминаний |
| `/delete [id]` | Удалить напоминание по ID |

---

## ⚙️ Переменные окружения / Environment Variables

| Переменная | Обязательна | По умолчанию | Описание |
|-----------|------------|--------------|----------|
| `BOT_TOKEN` | ✅ Да | — | Токен от @BotFather |
| `MODE` | Нет | `polling` | `polling` или `webhook` |
| `WEBHOOK_URL` | Только webhook | — | URL вашего сервера с HTTPS |
| `WEBHOOK_PORT` | Нет | `8443` | Порт для webhook-сервера |
| `WEBHOOK_SECRET` | Нет | — | Секрет для верификации webhook |
| `WHISPER_MODEL_SIZE` | Нет | `small` | `tiny` / `small` / `medium` |
| `DB_PATH` | Нет | `reminders.db` | Путь к SQLite базе данных |

---

## 🚀 Деплой на сервер (Webhook) / Server Deployment

Полный пошаговый план для **VPS REG.RU**: домен, DNS, HTTPS (Let's Encrypt), загрузка через **WinSCP**, Nginx, systemd — в файле **[DEPLOY_VPS_REGRU.md](DEPLOY_VPS_REGRU.md)**.

**Кратко / Summary:** нужны публичный IP, домен с HTTPS, Python 3.11+, ffmpeg; для webhook задайте в `.env` переменные из таблицы выше (`WEBHOOK_URL` — базовый HTTPS-адрес **без** `/webhook`).

---

## 🧠 Как это работает / How It Works

```
Голосовое сообщение → faster-whisper (offline STT)
                     → dateparser (NLP дата/время)
                     → SQLite (сохранение)
                     → APScheduler (таймер)
                     → Telegram уведомление
```

**STT (Speech-to-Text):** Используется [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — бесплатная offline версия Whisper от OpenAI. Работает полностью локально, без отправки аудио на внешние сервисы. Модель `small` (~244MB) обеспечивает хороший баланс точности и скорости.

---

## 📦 Зависимости / Dependencies

| Пакет | Назначение |
|-------|-----------|
| aiogram | Telegram Bot framework |
| faster-whisper | Offline speech recognition |
| pydub | Audio format conversion |
| dateparser | Natural language date parsing |
| apscheduler | Reminder scheduling |
| aiosqlite | Async SQLite database |
| pytz | Timezone handling |
| python-dotenv | .env file loading |

---

## 🔒 Безопасность / Security

- Токен бота хранится только в `.env` (не в коде)
- `.env` добавлен в `.gitignore`
- Все SQL запросы используют параметризацию
- Webhook защищён секретным токеном

---

## 📄 Лицензия / License

MIT License — используйте свободно.

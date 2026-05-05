"""
beforeShellExecution hook — warns if .env is missing before running the bot.
Reads JSON from stdin, outputs JSON to stdout.
"""
import json
import os
import sys
from pathlib import Path


def find_env_file() -> Path | None:
    """Search for .env file up to 4 directory levels up from cwd."""
    current = Path.cwd()
    for _ in range(4):
        candidate = current / ".env"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    command: str = ""
    for key in ("command", "cmd", "shell_command"):
        if key in data:
            command = str(data[key])
            break

    # Only intercept commands that run main.py
    if "main.py" not in command:
        print(json.dumps({"permission": "allow"}))
        return

    env_path = find_env_file()

    if env_path is None:
        print(json.dumps({
            "permission": "ask",
            "user_message": (
                "⚠️ Файл .env не найден!\n\n"
                "Перед запуском бота:\n"
                "1. Скопируйте .env.example → .env\n"
                "2. Заполните BOT_TOKEN (получить у @BotFather)\n"
                "3. Запустите бота снова"
            ),
            "agent_message": (
                ".env file not found. The bot requires BOT_TOKEN in .env to start. "
                "Create .env from .env.example and fill in the BOT_TOKEN."
            ),
        }))
        return

    # Read BOT_TOKEN value
    bot_token = ""
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("BOT_TOKEN="):
                bot_token = line.split("=", 1)[1].strip()
                break
    except Exception:
        pass

    if not bot_token or bot_token == "your_bot_token_here":
        print(json.dumps({
            "permission": "ask",
            "user_message": (
                "⚠️ BOT_TOKEN не заполнен в .env!\n\n"
                "Получите токен у @BotFather в Telegram:\n"
                "1. Откройте @BotFather\n"
                "2. Отправьте /newbot\n"
                "3. Скопируйте токен в .env:\n"
                "   BOT_TOKEN=123456:ABC-DEF..."
            ),
            "agent_message": (
                "BOT_TOKEN in .env is empty or still a placeholder. "
                "User must obtain a real token from @BotFather."
            ),
        }))
        return

    print(json.dumps({"permission": "allow"}))


if __name__ == "__main__":
    main()

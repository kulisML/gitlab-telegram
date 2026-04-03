import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, Header, HTTPException
from aiogram.enums import ParseMode

from core.config import config
from core.bot import bot, dp
from core import database as db
from core.scheduler import start_scheduler
from utils.formatters import FORMATTERS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure data directory exists (legacy JSON архив)
os.makedirs(config.DATA_DIR, exist_ok=True)

app = FastAPI(title="GitLab to Telegram Notifier")


def save_webhook_payload(event: str, data: dict):
    """Сохраняет payload в JSON-файл (архив)."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        daily_dir = os.path.join(config.DATA_DIR, today)
        os.makedirs(daily_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%H-%M-%S_%f")
        filepath = os.path.join(daily_dir, f"{timestamp}_{event}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Webhook payload saved: %s", filepath)
    except Exception as e:
        logger.error("Failed to save webhook payload: %s", e)


@app.post("/tgbotgit")
async def gitlab_webhook(request: Request, x_gitlab_token: Optional[str] = Header(None)):
    """Принимает GitLab Webhook и отправляет уведомление в Telegram."""

    # Верификация токена
    if config.GITLAB_SECRET_TOKEN and x_gitlab_token != config.GITLAB_SECRET_TOKEN:
        logger.warning("Invalid X-Gitlab-Token!")
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        data = await request.json()
    except Exception as e:
        logger.error("JSON parsing error: %s", e)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    object_kind = data.get("object_kind") or data.get("event_name") or data.get("event_type")
    logger.info("Received GitLab event: %s", object_kind)

    # Сохраняем в JSON-архив
    save_webhook_payload(object_kind or "unknown", data)

    # Определяем актора (GitLab username автора события)
    actor_gitlab = (
        data.get("user_name") or
        data.get("user", {}).get("username") or
        data.get("user", {}).get("name") or
        data.get("commit", {}).get("author", {}).get("name")
    )
    project = data.get("project", {}).get("name") or data.get("project_name")

    # Сохраняем в SQLite
    await db.save_event(
        event_type=object_kind or "unknown",
        project=project,
        actor_gitlab=actor_gitlab,
        data_json=json.dumps(data, ensure_ascii=False),
    )

    # Проверяем включено ли событие
    enabled_raw = await db.get_setting("enabled_events", "push,tag_push,merge_request,pipeline,issue,note,build,wiki_page")
    enabled_events = [e.strip() for e in enabled_raw.split(",")]
    if object_kind not in enabled_events:
        logger.info("Event '%s' is disabled in settings.", object_kind)
        return {"status": "ignored", "reason": "event_disabled"}

    # Форматируем сообщение
    formatter = FORMATTERS.get(object_kind)
    if not formatter:
        logger.info("Event '%s' ignored (no formatter).", object_kind)
        return {"status": "ignored", "reason": "no_formatter"}

    message = await formatter(data)

    # Отправляем в Telegram
    if message:
        try:
            await bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            logger.info("Notification sent to Telegram.")
        except Exception as e:
            logger.error("Telegram API error: %s", e)
            return {"status": "error", "message": str(e)}

    return {"status": "ok"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "bot_initialized": bool(bot.token),
        "data_dir": config.DATA_DIR,
        "version": "2.0.0"
    }


async def start_fastapi():
    """Запускает FastAPI через uvicorn."""
    server_config = uvicorn.Config(
        app=app,
        host=config.APP_HOST,
        port=config.APP_PORT,
        log_level="info"
    )
    server = uvicorn.Server(server_config)
    await server.serve()


async def start_bot_polling():
    """Запускает Telegram Bot в режиме polling."""
    logger.info("Starting Telegram bot polling...")
    await dp.start_polling(bot)


async def main():
    """Запускает все компоненты параллельно."""
    # Инициализация БД
    await db.init_db()
    logger.info("Starting GitLab→Telegram Bot v2.0")

    await asyncio.gather(
        start_fastapi(),
        start_bot_polling(),
        start_scheduler(),
    )


if __name__ == "__main__":
    asyncio.run(main())

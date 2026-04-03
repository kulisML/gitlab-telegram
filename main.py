import os
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, Header, HTTPException
from aiogram.enums import ParseMode

from core.config import config
from core.bot import bot
from utils.formatters import FORMATTERS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs(config.DATA_DIR, exist_ok=True)

app = FastAPI(title="GitLab to Telegram Notifier")

def save_webhook_payload(event: str, data: dict):
    """Saves the raw webhook payload to a JSON file for collection/audit."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        daily_dir = os.path.join(config.DATA_DIR, today)
        os.makedirs(daily_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%H-%M-%S_%f")
        filename = f"{timestamp}_{event}.json"
        filepath = os.path.join(daily_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Webhook payload saved: {filepath}")
    except Exception as e:
        logger.error(f"Failed to save webhook payload: {e}")

@app.post("/tgbotgit")
async def gitlab_webhook(request: Request, x_gitlab_token: Optional[str] = Header(None)):
    """Main endpoint to receive GitLab webhooks."""
    
    # Verify secret token if configured
    if config.GITLAB_SECRET_TOKEN and x_gitlab_token != config.GITLAB_SECRET_TOKEN:
        logger.warning(f"Invalid X-Gitlab-Token received! Expected: {config.GITLAB_SECRET_TOKEN}")
        raise HTTPException(status_code=403, detail="Invalid token")
    
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"JSON parsing error: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Detect event type (object_kind for most, or custom headers/fields)
    object_kind = data.get("object_kind")
    if not object_kind:
        # Some GitLab events might use different identifiers
        object_kind = data.get("event_name") or data.get("event_type")
    
    logger.info(f"Received GitLab event: {object_kind}")
    
    # Save the payload for "collection"
    save_webhook_payload(object_kind or "unknown", data)
    
    # Format message based on event type
    formatter = FORMATTERS.get(object_kind)
    if not formatter:
        logger.info(f"Event '{object_kind}' ignored (no formatter found).")
        return {"status": "ignored", "reason": "no_formatter"}

    message = formatter(data)
    
    # Send to Telegram
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
            logger.error(f"Telegram API error: {e}")
            return {"status": "error", "message": str(e)}

    return {"status": "ok"}

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "bot_initialized": bool(bot.token),
        "data_dir": config.DATA_DIR
    }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {config.APP_HOST}:{config.APP_PORT}")
    uvicorn.run(app, host=config.APP_HOST, port=config.APP_PORT)

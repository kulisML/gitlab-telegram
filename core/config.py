import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID")
    GITLAB_SECRET_TOKEN: Optional[str] = os.getenv("GITLAB_SECRET_TOKEN")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))
    DATA_DIR: str = os.getenv("DATA_DIR", "data/webhooks")

config = Config()

if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
    import logging
    logging.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set in environment variables!")

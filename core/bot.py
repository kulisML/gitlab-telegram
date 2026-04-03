from aiogram import Bot, Dispatcher
from .config import config

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

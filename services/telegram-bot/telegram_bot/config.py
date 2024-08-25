from os import getenv

class Config:
    class Telegram:
        TOKEN: str = getenv('TELEGRAM_BOT_TOKEN') or ""
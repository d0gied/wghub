from os import getenv


class Config:
    class Telegram:
        TOKEN: str = getenv("TELEGRAM_BOT_TOKEN") or ""

    class WireguardApi:
        HOST: str = getenv("WIREGUARD_API_HOST") or "localhost"
        PORT: int = int(getenv("WIREGUARD_API_PORT") or 8000)
        AUTH_TOKEN: str = getenv("WIREGUARD_API_AUTH_TOKEN") or ""

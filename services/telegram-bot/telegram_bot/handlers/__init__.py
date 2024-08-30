from aiogram import Router as AiogramRouter, Dispatcher
from loguru import logger
from importlib import import_module
from os import listdir


class Router(AiogramRouter):
    _routers: list[AiogramRouter] = []

    def __init__(self, *, name: str | None = None):
        super().__init__(name=name)
        self._routers.append(self)
        logger.debug(f"Router {self.name} created")

    @classmethod
    def init_all(cls, dp: Dispatcher):
        logger.debug("Initializing routers")
        for router in cls._routers:
            dp.include_router(router)
            logger.debug(f"Router {router.name} initialized")


for module in listdir("telegram_bot/handlers"):
    if module.endswith(".py") and module != "__init__.py":
        import_module(f"telegram_bot.handlers.{module[:-3]}")
        logger.debug(f"Imported handlers from {module}")

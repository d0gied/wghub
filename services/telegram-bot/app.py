from telegram_bot.config import Config
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from loguru import logger
from telegram_bot.handlers import Router

from asyncio import run


dp = Dispatcher()
Router.init_all(dp)

commands = [
    ("start", "Start the bot"),
    ("interfaces", "List all interfaces"),
]


async def update_commands(bot: Bot):
    _commands = await bot.get_my_commands()
    if _commands != commands:
        logger.info("Updating commands")
        await bot.set_my_commands(
            [
                types.BotCommand(command=command, description=description)
                for command, description in commands
            ]
        )
    logger.info("Commands are up to date")


async def main():
    bot = Bot(
        token=Config.Telegram.TOKEN,
        default=DefaultBotProperties(
            parse_mode="HTML",
        ),
    )
    await update_commands(bot)
    logger.info("Starting polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    run(main())

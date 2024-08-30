from aiogram import types
from aiogram.filters import Command
from ..api import WireguardApi, Interface, Peer
from . import Router

wg_api = WireguardApi()
router = Router(name="info")


@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Welcome to d0gied's wireguard bot!")

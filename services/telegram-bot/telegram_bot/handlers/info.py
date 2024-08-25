from aiogram import Router, types
from aiogram.filters import Command


router = Router()

@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Welcome to d0gied's wireguard bot!")


@router.message(Command("interfaces"))
async def interfaces(message: types.Message):
    await message.answer("Interfaces")
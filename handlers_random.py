from aiogram import F, Router
import random
import string
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from database import add_user


router_random = Router()


@router_random.message(Command("start"))
async def cmd_start(message: Message):
    add_user(message.from_user.id, message.from_user.username)
    await message.answer("Привет! Я тебя запомнил 😎")


@router_random.message(Command('кубик'))
async def cmd_dice(message: Message):
    value = random.randint(1, 6)
    await message.answer(f"Тебе выпало: {value} 🎲")


@router_random.message(Command('монетка'))
async def cmd_coins(message: Message):
    coins = ['Решка', 'Орел']
    winner = random.choice(coins)
    await message.answer(f'Тебе выпало: {winner} ')


@router_random.message(F.text.lower().startswith('выбери'))
async def chois(message: Message):
    user_text = message.text
    parts = user_text.split(':')
    parts1 = parts[1]
    options = parts1.split(',')
    winner = random.choice(options)
    await message.answer(f'Я выбирая: {winner}')


@router_random.message(F.text.lower().startswith('пароль'))
async def key(message: Message):
    user_text = message.text
    parts = user_text.split(' ')
    letters = string.ascii_letters
    digits = string.digits
    punctuation = "!@#$%"
    all_chars = letters + digits + punctuation
    parts1 = int(parts[1])
    winner = random.choices(all_chars, k=parts1)
    await message.answer(f'Твой пароль: {"".join(winner)}')
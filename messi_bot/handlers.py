import asyncio
import base64
import logging
from collections import defaultdict

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

import brain
import db
import pet
from config import FAMILY

router = Router()

# Пишем только своей семье
router.message.filter(F.from_user.id.in_(set(FAMILY)))
stranger_router = Router()

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='🍖 Покормить'), KeyboardButton(text='🦮 Гулять')],
        [KeyboardButton(text='🎾 Играть'), KeyboardButton(text='🤗 Погладить')],
        [KeyboardButton(text='📊 Как ты?')],
    ],
    resize_keyboard=True,
    input_field_placeholder='Напиши Месси…',
)

BUTTONS = {
    '🍖 Покормить': ('feed', 'насыпал(а) Месси вкусный корм в миску'),
    '🦮 Гулять': ('walk', 'взял(а) поводок и повёл(а) Месси гулять'),
    '🎾 Играть': ('play', 'кинул(а) Месси её любимую игрушку'),
    '🤗 Погладить': ('pet', 'гладит Месси и чешет ей пузико'),
}

# Чтобы два быстрых сообщения подряд не перепутали память
locks = defaultdict(asyncio.Lock)


def make_relay(bot: Bot):
    async def relay(user_id, text):
        if db.get_user(user_id) is None:
            return False
        await bot.send_message(user_id, text)
        db.add_message(user_id, 'assistant', text)
        db.touch_bot(user_id)
        return True
    return relay


async def answer_with_brain(message: Message, text, image=None):
    user_id = message.from_user.id
    async with locks[user_id]:
        db.add_user(user_id, message.from_user.username)
        db.touch_user(user_id)
        pet.apply('chat')
        await message.bot.send_chat_action(message.chat.id, 'typing')
        try:
            answer = await brain.reply(user_id, text, make_relay(message.bot), image=image)
        except Exception:
            logging.exception('Brain failed')
            answer = 'Хрр… я задремала и не расслышала 😴 Напиши ещё разочек?'
        await message.answer(answer[:4000], reply_markup=keyboard)
        db.touch_bot(user_id)


@router.message(CommandStart())
async def cmd_start(message: Message):
    db.add_user(message.from_user.id, message.from_user.username)
    name = FAMILY[message.from_user.id]
    await message.answer(
        f'Гав-гав! 🐾 {name.capitalize()}, это я, Месси! Теперь я могу тебе писать!\n\n'
        'Пиши мне что угодно — я всё запомню. А ещё меня можно кормить, гулять и гладить кнопками снизу 💕',
        reply_markup=keyboard,
    )


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer(
        '🐶 Просто пиши мне, присылай фото — я отвечу и запомню важное.\n\n'
        '/memory — что я помню\n'
        '/forget 12 — забыть факт №12\n'
        '/status — как я себя чувствую\n'
        '/clear — забыть нашу переписку (память о фактах останется)',
        reply_markup=keyboard,
    )


@router.message(Command('memory'))
async def cmd_memory(message: Message):
    memories = db.get_memories_for(message.from_user.id)
    if not memories:
        await message.answer('Моя голова пока пустая, как миска после ужина 🥣')
        return
    lines = [f"#{m['id']} {'🤫 ' if m['secret'] else ''}{m['fact']}" for m in memories]
    text = '🧠 Вот что я помню:\n\n' + '\n'.join(lines)
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i + 4000])


@router.message(Command('forget'))
async def cmd_forget(message: Message, command: CommandObject):
    if not command.args or not command.args.strip().lstrip('#').isdigit():
        await message.answer('Напиши номер, например: /forget 12 (номера есть в /memory)')
        return
    if db.delete_memory(int(command.args.strip().lstrip('#')), message.from_user.id):
        await message.answer('Всё, забыла 🙈')
    else:
        await message.answer('Не нашла такого воспоминания 🤔')


@router.message(Command('status'))
@router.message(F.text == '📊 Как ты?')
async def cmd_status(message: Message):
    await message.answer(pet.bars(pet.load()))
    await answer_with_brain(message, 'Как ты себя чувствуешь?')


@router.message(Command('clear'))
async def cmd_clear(message: Message):
    db.clear_history(message.from_user.id)
    await message.answer('Переписку забыла, но всё важное помню 🐾')


@router.message(F.text.in_(BUTTONS))
async def pet_action(message: Message):
    action, description = BUTTONS[message.text]
    pet.apply(action)
    await answer_with_brain(message, description)


@router.message(F.photo)
async def on_photo(message: Message):
    file = await message.bot.download(message.photo[-1])
    data = base64.standard_b64encode(file.read()).decode()
    await answer_with_brain(message, message.caption or '', image=('image/jpeg', data))


@router.message(F.sticker)
async def on_sticker(message: Message):
    await answer_with_brain(message, f'[стикер {message.sticker.emoji or ""}]')


@router.message(F.text)
async def on_text(message: Message):
    await answer_with_brain(message, message.text)


@router.message()
async def on_other(message: Message):
    await message.answer('Хрю? 🐽 Я пока понимаю только текст, фото и стикеры')


@stranger_router.message()
async def on_stranger(message: Message):
    await message.answer('Гав! 🐾 Я Месси, и я разговариваю только со своей семьёй.')

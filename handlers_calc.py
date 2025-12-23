from aiogram import F, Router
from aiogram.types import Message

router_calc = Router()

@router_calc.message(F.text.lower().startswith('посчитай'))
async def calc(message: Message):
    try:
        user_text = message.text
        parts = user_text.split(':')
        if len(parts) < 2:
            await message.answer("Пиши так: Посчитай: 2+2")
            return
        parts1 = parts[1]
        answer = eval(parts1)
        await message.answer(f'Ответ: {answer}')
    except Exception:
        await message.answer("Ошибка! Пиши только цифры.")
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime
router_data = Router()

class ReminderForm(StatesGroup):
    for_text = State()
    for_datetime = State()

@router_data.message(Command('запомнить'))
async def remember_start(message: Message, state: FSMContext):
    await message.answer('Что запомнить?')
    await state.set_state(ReminderForm.for_text)

@router_data.message(ReminderForm.for_text)
async def process_text(message: Message, state: FSMContext):
    await state.update_data(event_text=message.text)
    await message.answer('Напишите время и дату')
    await state.set_state(ReminderForm.for_datetime)

@router_data.message(ReminderForm.for_datetime)
async def process_datetime(message: Message, state: FSMContext):
    data = await state.get_data()
    dt_text = message.text
    event_text = data.get('event_text')

    try:
        remind_time = datetime.strptime(dt_text, "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("Неправильный формат. Пиши: 25.12.2025 18:30")
        return  # выходим, не создаём напоминание


    if remind_time <= datetime.now():
        await message.answer("Дата должна быть в будущем!")
        await state.clear()
        return

    asyncio.create_task(send_reminder(message.chat.id, event_text, remind_time))

    await message.answer(f"✅ Напоминание создано на {remind_time.strftime('%d.%m.%Y %H:%M')}")
    await state.clear()

async def send_reminder(chat_id, event_text, remind_time):
    from run import bot
    await asyncio.sleep((remind_time - datetime.now()).total_seconds())
    await bot.send_message(chat_id, f"⏰ Напоминание!\n\n{event_text}")
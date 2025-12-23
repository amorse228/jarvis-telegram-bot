from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


router_profile = Router()


class ReminderForm(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_hobby = State()

@router_profile.message(Command('profile'))
async def w_name(message: Message, state: FSMContext):
    await message.answer('Как тебя зовут?')
    await state.set_state(ReminderForm.waiting_name)

@router_profile.message(ReminderForm.waiting_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('Сколько тебе лет?')
    await state.set_state(ReminderForm.waiting_age)

@router_profile.message(ReminderForm.waiting_age)
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer('Твое хобби?')
    await state.set_state(ReminderForm.waiting_hobby)

@router_profile.message(ReminderForm.waiting_hobby)
async def process_hoddy(message: Message, state:FSMContext):
    await state.update_data(hobby=message.text)
    data = await state.get_data()
    text = (
        f'АНКЕТА\n\n'
        f'Имя: {data["name"]}\n'
        f'Возраст: {data["age"]}\n'
        f'Хобби: {message.text}'
    )
    await message.answer(text)
    await state.clear()

@router_profile.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer('Все команды:' )

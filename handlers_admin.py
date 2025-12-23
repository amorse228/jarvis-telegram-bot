from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database import get_all_users
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

router_admin = Router()

Admin_id = 1270318984

main_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Статистика", callback_data="admin_stats"),
     InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")]
])
class AdminState(StatesGroup):
    waiting_message = State()
    waiting_send = State()

@router_admin.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != Admin_id:
        await message.answer("У вас нет прав")
        return
    await message.answer(f"Привет, Создатель! Выбери действие:", reply_markup=main_kb)

@router_admin.callback_query(F.data == 'admin_stats')
async def cmd_stats(callback: CallbackQuery):
    count = len(get_all_users())
    await callback.answer()
    await callback.message.answer(f"В базе данных {count} человек")


@router_admin.callback_query(F.data == 'admin_broadcast')
async def cmd_send(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Что отправить пользователю")
    await state.set_state(AdminState.waiting_message)

@router_admin.message(AdminState.waiting_message)
async def cmd_waiting(message: Message, state: FSMContext):
    await message.copy_to(chat_id=message.chat.id)
    await state.update_data(msg_id=message.message_id)
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="send_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="send_cancel")
        ]
    ])
    await message.answer("Вот так будет выглядеть пост. Отправляем?", reply_markup=confirm_kb)
    await state.set_state(AdminState.waiting_send)


@router_admin.callback_query(F.data == "send_confirm", AdminState.waiting_send)
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    msg_id = data['msg_id']
    users = get_all_users()
    count = 0

    await callback.message.edit_text(f"🚀 Рассылка началась на {len(users)} человек...")

    for user in users:
        user_id = user[0]
        try:

            await callback.bot.copy_message(
                chat_id=user_id,
                from_chat_id=callback.from_user.id,
                message_id=msg_id
            )
            count += 1
        except Exception:
            pass

    # 5. Финал
    await callback.message.answer(f"✅ Готово! Отправлено: {count}")
    await state.clear()

@router_admin.callback_query(F.data == 'send_cancel', AdminState.waiting_send)
async def process(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🚫 Рассылка отменена.")
    await state.clear()





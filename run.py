import asyncio
from aiogram import Bot, Dispatcher
from ALL.jarvis_bot.handlers_profile import router_profile
from ALL.jarvis_bot.handlers_random import router_random
from ALL.jarvis_bot.handlers_data import router_data
from ALL.jarvis_bot.handlers_calc import router_calc
from ALL.jarvis_bot.handlers_admin import router_admin
from database import create_table



bot = Bot(token='8312162035:AAHNkjh1YpumPeO_tKLeE-VZw6i1T6EudHw')
dp = Dispatcher()

async def main():
    dp.include_router(router_profile)
    dp.include_router(router_random)
    dp.include_router(router_data)
    dp.include_router(router_calc)
    dp.include_router(router_admin)
    create_table()
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')


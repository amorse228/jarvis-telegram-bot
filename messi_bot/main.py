import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

import scheduler
from config import BOT_TOKEN, PROACTIVE_MESSAGES
from db import create_tables
from handlers import router, stranger_router


async def main():
    logging.basicConfig(level=logging.INFO)
    create_tables()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    dp.include_router(stranger_router)

    await bot.set_my_commands([
        BotCommand(command='memory', description='Что Месси помнит'),
        BotCommand(command='status', description='Как себя чувствует Месси'),
        BotCommand(command='help', description='Что умеет Месси'),
    ])

    if PROACTIVE_MESSAGES:
        asyncio.create_task(scheduler.run(bot))

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')

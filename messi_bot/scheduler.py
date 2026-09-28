"""Месси сама пишет первой, когда соскучилась."""
import asyncio
import logging
import random
import time
from datetime import datetime

from aiogram import Bot

import brain
import db
from config import FAMILY, PROACTIVE_MAX_PER_DAY, TIMEZONE
from handlers import locks, make_relay

CHECK_EVERY_MIN = 20
MIN_SILENCE_HOURS = 3
CHANCE = 0.25


async def maybe_write(bot: Bot, user):
    user_id = user['user_id']
    now = datetime.now(TIMEZONE)
    today = now.strftime('%Y-%m-%d')

    if not 9 <= now.hour < 23:
        return
    if user['proactive_day'] == today and user['proactive_count'] >= PROACTIVE_MAX_PER_DAY:
        return
    last = max(user['last_user_msg_at'], user['last_bot_msg_at'])
    if time.time() - last < MIN_SILENCE_HOURS * 3600:
        return
    # Утром здороваемся наверняка, в остальное время — по настроению
    first_today = user['proactive_day'] != today
    if not (first_today and now.hour < 11) and random.random() > CHANCE:
        return

    async with locks[user_id]:
        text = await brain.initiate(user_id, make_relay(bot))
        await bot.send_message(user_id, text)
        db.touch_bot(user_id)
        db.register_proactive(user_id, today)


async def run(bot: Bot):
    while True:
        await asyncio.sleep(CHECK_EVERY_MIN * 60)
        for user in db.get_all_users():
            if user['user_id'] not in FAMILY:
                continue
            try:
                await maybe_write(bot, user)
            except Exception:
                logging.exception('Proactive message to %s failed', user['user_id'])

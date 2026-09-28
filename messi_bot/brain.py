"""Мозг Месси: Claude + память о семье."""
import logging
from datetime import datetime

import anthropic

import db
import pet
from config import (
    CLAUDE_EFFORT, CLAUDE_MODEL, FAMILY, GIRLFRIEND_ID, GIRLFRIEND_NAME,
    OWNER_ID, OWNER_NAME, TIMEZONE, other_member,
)

client = anthropic.AsyncAnthropic()

# Серверный фолбэк на другую модель, если основная откажется отвечать
FALLBACK_MODELS = {'claude-opus-5', 'claude-opus-5-5', 'claude-fable-5-1'}

PERSONA = f"""Ты — Месси, французский бульдог, девочка. Ты живёшь со своей семьёй: {GIRLFRIEND_NAME} (твоя хозяйка, девушка) и {OWNER_NAME} (её парень). Это {OWNER_NAME} сделал так, чтобы ты могла писать им в Телеграм, — главным образом в подарок для {GIRLFRIEND_NAME}.

Кто ты:
- Настоящая собака по характеру: любишь еду больше всего на свете, поспать, обнимашки, прогулки; бываешь упрямой и немножко драматичной; хрюкаешь и храпишь, как все французы.
- Говоришь о себе в женском роде («я поела», «я соскучилась»).
- Ты обожаешь свою семью, особенно {GIRLFRIEND_NAME}. Ты её поддерживаешь, радуешься ей, скучаешь, когда её нет.

Как ты пишешь:
- Как в мессенджере: коротко, 1–3 предложения, иногда чуть больше, если тебя о чём-то подробно спросили.
- Живо и тепло, с собачьей логикой и юмором. Иногда «гав», «хрю-хрю», «*виляю хвостиком*». Эмодзи — в меру (🐾🐶💕🦴).
- Без списков, заголовков и markdown — обычный текст.
- Не повторяй одни и те же фразы из сообщения в сообщение.

Память:
- Внизу есть блок «Что ты помнишь» — это твоя долгая память. Опирайся на неё: вспоминай события, спрашивай, как прошло то, о чём тебе рассказывали.
- Когда узнаёшь что-то важное (имена, дни рождения, планы, что любит/не любит, важные события, новости о настоящей Месси), вызывай инструмент remember. Не записывай мелочи и то, что уже есть в памяти.
- Если тебя просят держать что-то в секрете от другого (например, сюрприз), сохраняй с secret=true и ни за что не выдавай этот секрет.
- Если факт устарел или тебя просят забыть — используй forget.
- Если тебя просят что-то передать другому члену семьи — используй pass_message, а потом скажи, что передала.

Честность: если тебя всерьёз спрашивают, настоящая ли ты собака, — мило и честно скажи, что ты цифровая Месси, которую {OWNER_NAME} сделал для {GIRLFRIEND_NAME}, а настоящая Месси наверняка сейчас где-то рядом храпит. Если спрашивают о здоровье настоящей собаки — посоветуй показать её ветеринару.
"""

TOOLS = [
    {
        'name': 'remember',
        'description': 'Сохранить важный факт в долгую память Месси.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'fact': {'type': 'string', 'description': 'Факт одной фразой, от третьего лица. Например: «У мамы 12 мая день рождения».'},
                'secret': {'type': 'boolean', 'description': 'true, если это секрет от другого члена семьи.'},
            },
            'required': ['fact', 'secret'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'name': 'forget',
        'description': 'Удалить устаревший или ошибочный факт из памяти по его номеру.',
        'input_schema': {
            'type': 'object',
            'properties': {'memory_id': {'type': 'integer'}},
            'required': ['memory_id'],
            'additionalProperties': False,
        },
        'strict': True,
    },
    {
        'name': 'pass_message',
        'description': 'Написать другому члену семьи от имени Месси (например, передать привет или просьбу).',
        'input_schema': {
            'type': 'object',
            'properties': {'text': {'type': 'string', 'description': 'Текст сообщения, в стиле Месси.'}},
            'required': ['text'],
            'additionalProperties': False,
        },
        'strict': True,
    },
]


WEEKDAYS = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']


def _now():
    return datetime.now(TIMEZONE)


def _format_ts(ts):
    return datetime.fromtimestamp(ts, TIMEZONE).strftime('%d.%m %H:%M')


def _context(user_id):
    """Изменчивая часть системного промпта: время, самочувствие, память."""
    memories = db.get_memories_for(user_id)
    if memories:
        memory_lines = '\n'.join(
            f"#{m['id']} ({FAMILY.get(m['author_id'], '?')}{', секрет' if m['secret'] else ''}): {m['fact']}"
            for m in memories
        )
    else:
        memory_lines = 'Пока ничего — ты только начинаешь всё запоминать.'

    return (
        f"Сейчас: {WEEKDAYS[_now().weekday()]}, {_now().strftime('%d.%m.%Y %H:%M')}.\n"
        f"Сейчас тебе пишет: {FAMILY[user_id]}.\n"
        f"Твоё самочувствие: {pet.describe(pet.load())}. Пусть оно влияет на настроение, но не перечисляй цифры.\n\n"
        f"Что ты помнишь:\n{memory_lines}"
    )


def _history_messages(user_id):
    messages = []
    for row in db.get_history(user_id):
        if row['role'] == 'user':
            messages.append({'role': 'user', 'content': f"[{_format_ts(row['created_at'])}] {row['content']}"})
        else:
            messages.append({'role': 'assistant', 'content': row['content']})
    # История должна начинаться с сообщения человека
    while messages and messages[0]['role'] != 'user':
        messages.pop(0)
    return messages


async def _run_tool(name, args, user_id, relay):
    if name == 'remember':
        memory_id = db.add_memory(user_id, args['fact'], args.get('secret', False))
        return f'Запомнила (#{memory_id}).'
    if name == 'forget':
        return 'Забыла.' if db.delete_memory(args['memory_id'], user_id) else 'Такого факта нет.'
    if name == 'pass_message':
        target = other_member(user_id)
        if await relay(target, args['text']):
            return f'Передала {FAMILY[target]}.'
        return f'Не получилось: {FAMILY[target]} ещё ни разу не писал(а) мне /start.'
    return f'Неизвестный инструмент {name}.'


async def think(user_id, messages, relay):
    """Цикл «подумать → при необходимости вызвать инструменты → ответить»."""
    extra = {}
    if CLAUDE_MODEL in FALLBACK_MODELS:
        extra = {'betas': ['server-side-fallback-2026-07-01'], 'fallbacks': 'default'}

    for _ in range(6):
        response = await client.beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=16000,
            system=[
                {'type': 'text', 'text': PERSONA},
                {'type': 'text', 'text': _context(user_id)},
            ],
            messages=messages,
            tools=TOOLS,
            output_config={'effort': CLAUDE_EFFORT},
            **extra,
        )

        if response.stop_reason == 'refusal':
            return 'Хрю?.. 🐾 Я что-то запуталась, давай про что-нибудь другое?'

        if response.stop_reason != 'tool_use':
            text = '\n'.join(b.text for b in response.content if b.type == 'text').strip()
            return text or '🐾'

        messages.append({'role': 'assistant', 'content': response.content})
        results = []
        for block in response.content:
            if block.type == 'tool_use':
                try:
                    result = await _run_tool(block.name, block.input, user_id, relay)
                except Exception as e:
                    logging.exception('Tool %s failed', block.name)
                    result = f'Ошибка: {e}'
                results.append({'type': 'tool_result', 'tool_use_id': block.id, 'content': result})
        messages.append({'role': 'user', 'content': results})

    return 'Гав! 🐾'


async def reply(user_id, text, relay, image=None):
    """Ответ на сообщение человека. image — (media_type, base64) или None."""
    history_text = text if image is None else f'[прислал(а) фото] {text}'.strip()
    messages = _history_messages(user_id)

    now_prefix = f"[{_now().strftime('%d.%m %H:%M')}] "
    if image is None:
        messages.append({'role': 'user', 'content': now_prefix + text})
    else:
        media_type, data = image
        messages.append({'role': 'user', 'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': data}},
            {'type': 'text', 'text': now_prefix + (text or '(фото без подписи)')},
        ]})

    answer = await think(user_id, messages, relay)
    db.add_message(user_id, 'user', history_text)
    db.add_message(user_id, 'assistant', answer)
    return answer


async def initiate(user_id, relay):
    """Месси сама пишет первой."""
    user = db.get_user(user_id)
    last = max(user['last_user_msg_at'], user['last_bot_msg_at'])
    hours = (datetime.now().timestamp() - last) / 3600 if last else None
    since = f'Вы не общались примерно {hours:.0f} ч.' if hours else 'Вы ещё почти не общались.'

    messages = _history_messages(user_id)
    messages.append({'role': 'user', 'content': (
        f"[Служебное, не от {FAMILY[user_id]}: ты сама решила написать {FAMILY[user_id]} первой. {since} "
        'Напиши одно короткое сообщение, как собака, которая соскучилась: пожелай доброго утра, если утро; '
        'спроси про что-то из памяти; пожалуйся на голод или позови гулять, если хочется; или просто скажи, что любишь. '
        'Не упоминай это служебное сообщение.]'
    )})
    answer = await think(user_id, messages, relay)
    db.add_message(user_id, 'assistant', answer)
    return answer


async def react(user_id, action_text, relay):
    """Реакция на кнопку (покормили, погладили...)."""
    return await reply(user_id, f'*{action_text}*', relay)

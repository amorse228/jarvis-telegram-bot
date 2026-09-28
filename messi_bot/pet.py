"""Состояние Месси как тамагочи: сытость, энергия, настроение меняются со временем."""
import time
from datetime import datetime

from config import TIMEZONE
from db import get_pet_state, save_pet_state

DEFAULT_STATE = {'satiety': 80, 'energy': 80, 'happiness': 80}

# Эффект действий: (сытость, энергия, настроение)
ACTIONS = {
    'feed': (40, 5, 10),
    'walk': (-10, -25, 30),
    'play': (-5, -15, 20),
    'pet': (0, 0, 15),
    'chat': (0, 0, 3),
}


def _clamp(value):
    return max(0.0, min(100.0, value))


def _decay(state):
    """Пересчитывает показатели с учетом прошедшего времени."""
    now = time.time()
    hours = (now - state.get('updated_at', now)) / 3600
    if hours > 0:
        sleeping = datetime.now(TIMEZONE).hour < 8
        state['satiety'] = _clamp(state['satiety'] - 5 * hours)
        state['happiness'] = _clamp(state['happiness'] - 3 * hours)
        state['energy'] = _clamp(state['energy'] + (10 if sleeping else -2) * hours)
    state['updated_at'] = now
    return state


def load():
    state = {**DEFAULT_STATE, **get_pet_state()}
    state = _decay(state)
    save_pet_state(state)
    return state


def apply(action):
    state = load()
    d_satiety, d_energy, d_happiness = ACTIONS[action]
    state['satiety'] = _clamp(state['satiety'] + d_satiety)
    state['energy'] = _clamp(state['energy'] + d_energy)
    state['happiness'] = _clamp(state['happiness'] + d_happiness)
    save_pet_state(state)
    return state


def _word(value, low, mid, high):
    if value < 30:
        return low
    if value < 65:
        return mid
    return high


def describe(state):
    """Описание самочувствия словами — для мозга Месси."""
    return (
        f"сытость {state['satiety']:.0f}/100 ({_word(state['satiety'], 'очень голодная', 'немного голодная', 'сытая')}), "
        f"энергия {state['energy']:.0f}/100 ({_word(state['energy'], 'сонная и уставшая', 'спокойная', 'полна сил')}), "
        f"настроение {state['happiness']:.0f}/100 ({_word(state['happiness'], 'грустит и скучает', 'нормальное', 'счастливая')})"
    )


def bars(state):
    """Описание для людей — с полосками."""
    def bar(value):
        filled = round(value / 10)
        return '█' * filled + '░' * (10 - filled)

    return (
        f"🍖 Сытость:   {bar(state['satiety'])} {state['satiety']:.0f}%\n"
        f"⚡ Энергия:    {bar(state['energy'])} {state['energy']:.0f}%\n"
        f"💖 Настроение: {bar(state['happiness'])} {state['happiness']:.0f}%"
    )

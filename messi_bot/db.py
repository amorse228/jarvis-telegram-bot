"""Память Месси: переписка, факты о семье, состояние питомца."""
import sqlite3
import time

from config import DB_PATH, HISTORY_LIMIT

connection = sqlite3.connect(DB_PATH, check_same_thread=False)
connection.row_factory = sqlite3.Row
cursor = connection.cursor()


def create_tables():
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        last_user_msg_at REAL DEFAULT 0,
        last_bot_msg_at REAL DEFAULT 0,
        proactive_day TEXT DEFAULT '',
        proactive_count INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        fact TEXT NOT NULL,
        secret INTEGER DEFAULT 0,
        created_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS pet_state (
        key TEXT PRIMARY KEY,
        value REAL NOT NULL
    );
    ''')
    connection.commit()


# ---------- пользователи ----------

def add_user(user_id, username):
    cursor.execute(
        'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
        (user_id, username),
    )
    connection.commit()


def get_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()


def get_all_users():
    cursor.execute('SELECT * FROM users')
    return cursor.fetchall()


def touch_user(user_id):
    cursor.execute('UPDATE users SET last_user_msg_at = ? WHERE user_id = ?', (time.time(), user_id))
    connection.commit()


def touch_bot(user_id):
    cursor.execute('UPDATE users SET last_bot_msg_at = ? WHERE user_id = ?', (time.time(), user_id))
    connection.commit()


def register_proactive(user_id, day):
    user = get_user(user_id)
    count = user['proactive_count'] + 1 if user['proactive_day'] == day else 1
    cursor.execute(
        'UPDATE users SET proactive_day = ?, proactive_count = ? WHERE user_id = ?',
        (day, count, user_id),
    )
    connection.commit()


# ---------- переписка ----------

def add_message(user_id, role, content):
    cursor.execute(
        'INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)',
        (user_id, role, content, time.time()),
    )
    connection.commit()


def get_history(user_id, limit=HISTORY_LIMIT):
    cursor.execute(
        'SELECT role, content, created_at FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?',
        (user_id, limit),
    )
    return list(reversed(cursor.fetchall()))


def clear_history(user_id):
    cursor.execute('DELETE FROM messages WHERE user_id = ?', (user_id,))
    connection.commit()


# ---------- долгая память (факты) ----------

def add_memory(author_id, fact, secret=False):
    cursor.execute(
        'INSERT INTO memories (author_id, fact, secret, created_at) VALUES (?, ?, ?, ?)',
        (author_id, fact, int(secret), time.time()),
    )
    connection.commit()
    return cursor.lastrowid


def get_memories_for(user_id):
    """Все общие факты + секреты, которые рассказал именно этот человек."""
    cursor.execute(
        'SELECT * FROM memories WHERE secret = 0 OR author_id = ? ORDER BY id',
        (user_id,),
    )
    return cursor.fetchall()


def delete_memory(memory_id, user_id):
    """Удалить можно общий факт или свой секрет, но не чужой секрет."""
    cursor.execute(
        'DELETE FROM memories WHERE id = ? AND (secret = 0 OR author_id = ?)',
        (memory_id, user_id),
    )
    connection.commit()
    return cursor.rowcount > 0


# ---------- состояние питомца ----------

def get_pet_state():
    cursor.execute('SELECT key, value FROM pet_state')
    return {row['key']: row['value'] for row in cursor.fetchall()}


def save_pet_state(state):
    cursor.executemany(
        'INSERT OR REPLACE INTO pet_state (key, value) VALUES (?, ?)',
        list(state.items()),
    )
    connection.commit()

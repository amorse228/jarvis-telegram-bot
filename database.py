import sqlite3

# Создаем подключение к файлу базы данных (он создастся сам)
connection = sqlite3.connect('bot_database.db')
cursor = connection.cursor()


# 1. Функция создания таблицы (запускается один раз при старте)
def create_table():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT
    )
    ''')
    connection.commit()


# 2. Функция добавления пользователя
def add_user(user_id, username):
    # Сначала проверяем, есть ли уже такой юзер в базе
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    # Если юзера нет — добавляем
    if user is None:
        cursor.execute('INSERT INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
        connection.commit()
        print(f"Пользователь {username} ({user_id}) добавлен в базу!")
    else:
        print(f"Пользователь {user_id} уже есть в базе.")


# 3. Функция чтобы достать ВСЕХ пользователей (для рассылки)
def get_all_users():
    cursor.execute('SELECT user_id FROM users')
    return cursor.fetchall()

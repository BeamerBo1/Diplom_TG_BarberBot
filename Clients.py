import sqlite3
import config
from aiogram import Bot, Dispatcher, executor, types
bot = Bot(token=config.TOKEN)
dp = Dispatcher(bot)
# Подключение к базе данных
conn, cursor = sqlite3.connect('diplom.db', check_same_thread=False), None

def add_user_to_database(user_id, username):
    cursor.execute("SELECT COUNT(*) FROM Users WHERE Chat_id=?", (user_id,))
    result = cursor.fetchone()
    if result[0] == 0:
        cursor.execute("INSERT INTO Users (Chat_id, Name) VALUES (?, ?)",
                       (user_id, username))
        conn.commit()
        print("Пользователь успешно добавлен в базу данных.")
    else:
        print("Пользователь уже существует в базе данных.")



cursor = conn.cursor()
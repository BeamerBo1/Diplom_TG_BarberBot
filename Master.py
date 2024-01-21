import sqlite3
import config
from aiogram import Bot, Dispatcher, executor, types
bot = Bot(token=config.TOKEN)
dp = Dispatcher(bot)
# Подключение к базе данных
conn, cursor = sqlite3.connect('diplom.db', check_same_thread=False), None

def is_Master(user_id):
    cursor.execute("SELECT COUNT(*) FROM Master WHERE Chat_id=?",(user_id,))
    result = cursor.fetchone()
    if result is not None:
        return result[0]
    return False



cursor = conn.cursor()
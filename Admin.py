from aiogram import types
from main import dp, conn, AddStates


bot = dp.bot

def is_Admin(user_id):
    cursor.execute("SELECT COUNT(*) FROM Admin WHERE Chat_id=?",(user_id,))
    result = cursor.fetchone()
    if result is not None:
        return result[0]
    return False

async def add_Master(message: types.Message):
    await AddStates.waiting_for_name.set() # Устанавливаем состояние ожидания имени мастера
    await bot.send_message(message.chat.id, "Введите имя нового мастера:")# Отправляем сообщение с запросом информации о новом мастере

async def edit_Master(message: types.Message):
    await AddStates.waiting_for_name.set()  # Устанавливаем состояние ожидания имени мастера
    await bot.send_message(message.chat.id, "Введите имя нового мастера:")# Отправляем сообщение с запросом информации о новом мастере

async def add_Service(message: types.Message):
    await AddStates.waiting_for_servicename.set()  # Устанавливаем состояние ожидания названия услуги
    await bot.send_message(message.chat.id, "Введите наименование новой услуги:")

def update_name_in_db(cursor, chosen_master_id, new_name):
    if new_name is not None:
        cursor.execute("UPDATE Master SET Name = ? WHERE ID = ?", (new_name, chosen_master_id))

def update_chat_id_in_db(cursor, chosen_master_id, new_chat_id):
    cursor.execute("UPDATE Master SET Chat_id = ? WHERE ID = ?", (new_chat_id, chosen_master_id))

def update_nameservice_in_db(cursor, chosen_service_id, new_names):
    if new_names is not None:
        cursor.execute("UPDATE Service SET Name = ? WHERE ID = ?", (new_names, chosen_service_id))

def update_time_in_db(cursor, chosen_service_id, new_time):
    if new_time is not None:
        cursor.execute("UPDATE Service SET Time = ? WHERE ID = ?", (new_time, chosen_service_id))

def update_price_in_db(cursor, chosen_service_id, new_price):
    if new_price is not None:
        cursor.execute("UPDATE Service SET Price = ? WHERE ID = ?", (new_price, chosen_service_id))


cursor = conn.cursor()




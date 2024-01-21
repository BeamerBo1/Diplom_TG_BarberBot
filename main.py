import asyncio

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ReplyKeyboardMarkup, \
    KeyboardButton, Contact, ContentType
from aiogram.utils.exceptions import MessageToEditNotFound

import Clients
import Master
import Admin
import config
import sqlite3
import logging
import calendar
import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Подключение к базе данных
conn, cursor = sqlite3.connect('diplom.db', check_same_thread=False), None
user_data = {}
invoice_messages = {}
if 'mess_data' not in globals():
    mess_data = {}
class AddStates(StatesGroup):
    waiting_for_service_confirmation = State()
    waiting_for_name = State()  # Ожидание Имени мастера
    waiting_for_chat_id = State()  # Ожидание ID чата мастера
    waiting_for_servicename = State() # Ожидание наименования услуги
    waiting_for_servicetime = State() # Ожидание ввода времени
    waiting_for_service_choice=State()
    waiting_for_serviceprice=State()

class AddUser(StatesGroup):
    waiting_user_name=State()
    waiting_phone_permission=State()

class AddMasterService(StatesGroup):
    waiting_for_masterservice_confirmation= State()

class ChooseTime(StatesGroup):
    chosen_hour = State()
class ChoosePhoneNumber(StatesGroup):
    waiting_for_phone_number=State()

class EditStates(StatesGroup):
    waiting_for_edit_choice = State()
    waiting_for_new_name = State()
    waiting_for_new_chat_id=State()

class EditServiceStates(StatesGroup):
    edit_choice = State()
    new_name = State()
    new_time = State()
    new_price=State()

class DeleteStates(StatesGroup):
    waiting_for_master_choice = State()
    waiting_for_confirmation = State()
    waiting_for_service_choice = State()
    waiting_for_serevice = State()

@dp.message_handler(lambda message: message.text == 'Я администратор')
async def handle_admin_activation(message: types.Message, state: FSMContext):
    cursor.execute("SELECT COUNT(*) FROM Admin")
    admin_count = cursor.fetchone()[0]
    if admin_count > 0:
        # Если администратор уже существует
        await message.answer("Извините, в данном боте уже имеется администратор.")
    else:
        # Если администратора нет, предложим добавить
        keyboard = InlineKeyboardMarkup()
        yes_button = InlineKeyboardButton("Да", callback_data="add_admin")
        no_button = InlineKeyboardButton("Нет", callback_data="deny_admin")
        keyboard.add(yes_button, no_button)

        # Отправляем сообщение с клавиатурой
        sent_message = await message.answer("Добавить вас в данную базу в роли администратора?", reply_markup=keyboard)

        # Сохраняем идентификатор отправленного сообщения в состоянии
        await state.update_data(sent_message_id=sent_message.message_id)

@dp.callback_query_handler(lambda query: query.data in {"add_admin", "deny_admin"})
async def handle_admin_callback(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sent_message_id = data.get("sent_message_id")
    adminadd_chat_id = call.from_user.id  # Сохраняем chat_id админа
    mess_data['adminadd_chat_id'] = adminadd_chat_id

    if call.data == "add_admin":
        # Получаем реальное имя пользователя из таблицы Users
        conn = sqlite3.connect('diplom.db')
        cursor = conn.cursor()

        cursor.execute("SELECT RealName FROM Users WHERE Chat_id = ?", (str(adminadd_chat_id),))
        result = cursor.fetchone()

        if result:
            real_name = result[0]

            # Добавляем пользователя в таблицу Admin
            cursor.execute("INSERT INTO Admin (Name, Chat_id, RealName) VALUES (?, ?, ?)",
                           (call.from_user.username, str(adminadd_chat_id), real_name))

            # Обновляем роль пользователя в таблице Users
            cursor.execute("DELETE FROM Users WHERE Chat_id = ?", (str(adminadd_chat_id),))

            # Сохраняем изменения
            conn.commit()

            # Закрываем соединение
            conn.close()

            keyboard = InlineKeyboardMarkup()
            reebood_btn = InlineKeyboardButton("Перезапустить", callback_data="reboot_btn")
            keyboard.add(reebood_btn)

            # Редактируем отправленное сообщение
            await bot.edit_message_text("Вы успешно добавлены в роли администратора. Перезапустите бота для дальнейшей работы.", call.message.chat.id, sent_message_id, reply_markup=keyboard)
        else:
            await call.answer("Ошибка: не удалось найти пользователя в таблице Users.")
    elif call.data == "deny_admin":
        # Редактируем отправленное сообщение
        await bot.edit_message_text("Вы отказались от роли администратора.", call.message.chat.id, sent_message_id)

    # Удаляем данные из состояния
    await state.finish()

@dp.callback_query_handler(lambda query: query.data == "reboot_btn")
async def handle_reboot_button(call: types.CallbackQuery):
    admin_id = mess_data['adminadd_chat_id']

    # Удаление предыдущего сообщения
    await bot.delete_message(admin_id, call.message.message_id)

    # Отправка нового сообщения с обычной клавиатурой
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    AddMaster = types.KeyboardButton('Мастера')
    AddService = types.KeyboardButton('Услуги')
    keyboard.add(AddMaster, AddService)
    welcome_message = "Добро пожаловать, Админ! Выберите действие:"
    await bot.send_message(admin_id, welcome_message, reply_markup=keyboard)

@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    user_id = message.from_user.id
    AdminStatus = Admin.is_Admin(user_id)
    MasterStatus = Master.is_Master(user_id)
    # Проверяем, является ли пользователь наставником
    if AdminStatus:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        AddMaster = types.KeyboardButton('Мастера')
        AddService = types.KeyboardButton('Услуги')
        Advertising= types.KeyboardButton('Рассылка')
        keyboard.add(AddMaster, AddService, Advertising)
        welcome_message = "Добро пожаловать, Админ! Выберите действие:"
        await  bot.send_message(message.chat.id, welcome_message, reply_markup=keyboard)

    if MasterStatus:
        welcome_message = "Добро пожаловать, Мастер! Выберите действие:"
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        MyRecords = types.KeyboardButton('Мои заявки')
        MyHour = types.KeyboardButton('Мои часы')
        MyDayOff = types.KeyboardButton('Мои выходные')
        keyboard.add(MyRecords, MyHour, MyDayOff)
        await  bot.send_message(message.chat.id, welcome_message, reply_markup=keyboard)

    if AdminStatus == 0 and MasterStatus == 0:
        chat_id = message.chat.id
        # Проверяем наличие пользователя в базе данных
        cursor.execute("SELECT * FROM Users WHERE Chat_id=?", (chat_id,))
        user_data = cursor.fetchone()

        if not user_data:
            # Если пользователя нет в базе или у него нет имени, просим представиться
            await bot.send_message(message.chat.id, "Добрый день! Вижу, что вы у нас впервые. Как я могу вас называть?")
            # Ожидаем ввода имени
            await AddUser.waiting_user_name.set()

        else:
            # Если у пользователя уже есть имя, используем его
            user_name = user_data[4]
            welcome_message = f"Здравствуйте, {user_name}! Выберите действие:"
            # Создаем клавиатуру
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            my_appointments_button = KeyboardButton("Мои актуальные записи")
            book_appointment_button = KeyboardButton("Записаться")
            cancel_entry = KeyboardButton("Отменить запись")

            # Добавляем кнопки на клавиатуру
            keyboard.add(my_appointments_button, book_appointment_button, cancel_entry)

            await bot.send_message(message.chat.id, welcome_message, reply_markup=keyboard)

        # Отправляем сообщение с клавиатурой


@dp.message_handler(state=AddUser.waiting_user_name)
async def add_users_name(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    username = message.from_user.username
    user_name = message.text

    cursor.execute("INSERT INTO Users (Name, Chat_id, RealName) VALUES (?, ?, ?)",
                   (username, chat_id, user_name))
    conn.commit()

    # Спрашиваем у пользователя, разрешает ли он добавить телефон
    keyboard = InlineKeyboardMarkup()
    allow_button = InlineKeyboardButton("Да", callback_data="allow_phone")
    deny_button = InlineKeyboardButton("Нет", callback_data="deny_phone")
    keyboard.add(allow_button, deny_button)

    sent_message = await bot.send_message(chat_id, f"{user_name}! Вы разрешите добавить ваш телефон?", reply_markup=keyboard)
    # Сохраняем message_id в состоянии FSM
    await state.update_data(message_id=sent_message.message_id)

    # Устанавливаем состояние FSM для ожидания ответа пользователя
    await AddUser.waiting_phone_permission.set()


@dp.callback_query_handler(lambda query: query.data in ["allow_phone", "deny_phone"],
                           state=AddUser.waiting_phone_permission)
async def handle_phone_permission(query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(query.id)

    # Получаем данные пользователя и состояние FSM
    user_id = query.from_user.id
    user_data = await state.get_data()
    message_id = user_data.get("message_id")

    if query.data == "allow_phone":
        # Если пользователь разрешил, отправляем новое сообщение и удаляем старое
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        reg_button = KeyboardButton(text="Отправить номер телефона", request_contact=True)
        keyboard.add(reg_button)

        new_message = await bot.send_message(user_id, "Отправьте ваш номер телефона, нажав на кнопку ниже", reply_markup=keyboard)

        # Удаляем старое сообщение
        await bot.delete_message(chat_id=user_id, message_id=message_id)

        # Сохраняем новый message_id в состоянии FSM
        await state.update_data(message_id=new_message.message_id)

        # Устанавливаем состояние FSM для ожидания номера телефона
        await AddUser.waiting_phone_permission.set()

    elif query.data == "deny_phone":
        # Если пользователь отказал, добавляем пустое значение в базу данных
        cursor.execute("UPDATE Users SET TelNumber = ? WHERE Chat_id = ?", (None, user_id))
        conn.commit()
        cursor.execute("SELECT * FROM Users WHERE Chat_id=?", (user_id,))
        user_data = cursor.fetchone()
        new_message = await bot.send_message(user_id, "Телефон не добавлен.")

        # Удаляем старое сообщение
        await bot.delete_message(chat_id=user_id, message_id=message_id)

        # Сохраняем новый message_id в состоянии FSM
        await state.update_data(message_id=new_message.message_id)
        user_name = user_data[4]
        welcome_message = f"Здравствуйте, {user_name}! Выберите действие:"
        # Создаем клавиатуру
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        my_appointments_button = KeyboardButton("Мои актуальные записи")
        book_appointment_button = KeyboardButton("Записаться")
        cancel_entry = KeyboardButton("Отменить запись")


        # Добавляем кнопки на клавиатуру
        keyboard.add(my_appointments_button, book_appointment_button,cancel_entry)

        await bot.send_message(query.message.chat.id, welcome_message, reply_markup=keyboard)

        # Сбрасываем состояние FSM
        await state.finish()


@dp.message_handler(content_types=types.ContentType.CONTACT, state=AddUser.waiting_phone_permission)
async def handle_contact(message: types.Message, state: FSMContext):
    contact: Contact = message.contact
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM Users WHERE Chat_id=?", (user_id,))
    user_data = cursor.fetchone()

    # Обновляем базу данных с номером телефона
    cursor.execute("UPDATE Users SET TelNumber = ? WHERE Chat_id = ?", (contact.phone_number, user_id))
    conn.commit()

    await bot.send_message(user_id, "Телефон успешно добавлен.")
    user_name = user_data[4]
    welcome_message = f"Здравствуйте, {user_name}! Выберите действие:"
    # Создаем клавиатуру
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    my_appointments_button = KeyboardButton("Мои актуальные записи")
    book_appointment_button = KeyboardButton("Записаться")
    cancel_entry = KeyboardButton("Отменить запись")

    # Добавляем кнопки на клавиатуру
    keyboard.add(my_appointments_button, book_appointment_button, cancel_entry)

    await bot.send_message(message.chat.id, welcome_message, reply_markup=keyboard)


    # Сбрасываем состояние FSM
    await state.finish()


class NewsletterStates(StatesGroup):
    AWAITING_TEXT = State()
@dp.message_handler(lambda message: message.text == 'Рассылка' and Admin.is_Admin(message.from_user.id))
async def start_newsletter(message: types.Message, state: FSMContext):
    # Создаем клавиатуру с двумя кнопками "Далее" и "Отмена"
    keyboard = types.InlineKeyboardMarkup()
    next_btn = types.InlineKeyboardButton("Далее", callback_data="newsletter_next")
    cancel_btn = types.InlineKeyboardButton("Отмена", callback_data="newsletter_cancel")
    keyboard.row(next_btn, cancel_btn)

    # Отправляем сообщение с клавиатурой и запоминаем его message_id
    msg = await message.answer("❗❗Внимание❗❗Следующее отправленное сообщение будет разослано всем пользователям:", reply_markup=keyboard)

    # Сохраняем message_id в состоянии для последующего редактирования
    await NewsletterStates.AWAITING_TEXT.set()
    await state.update_data(start_msg_id=msg.message_id)

@dp.callback_query_handler(lambda query: query.data == 'newsletter_next', state=NewsletterStates.AWAITING_TEXT)
async def newsletter_next(callback_query: types.CallbackQuery, state: FSMContext):
    # Получаем message_id из состояния
    state_data = await state.get_data()
    start_msg_id = state_data.get('start_msg_id')

    # Отправляем новое сообщение о том, что следующее отправленное сообщение будет разослано всем пользователям
    await bot.edit_message_text(" Отправьте текст для рассылки.", callback_query.from_user.id, start_msg_id)


    # Сохраняем callback_query_id в состоянии для последующего использования
    await state.update_data(callback_query_id=callback_query.id)

# ...

@dp.message_handler(state=NewsletterStates.AWAITING_TEXT)
async def process_newsletter_text(message: types.Message, state: FSMContext):
    text = message.text

    # Получаем всех пользователей из таблицы Users
    cursor.execute("SELECT Chat_id FROM Users")
    users = cursor.fetchall()

    # Отправляем сообщение каждому пользователю
    for user in users:
        try:
            await bot.send_message(user[0], text)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user[0]}: {e}")

    # Получаем данные из состояния
    state_data = await state.get_data()
    callback_query_id = state_data.get('callback_query_id')

    # Отвечаем на callback_query, чтобы закрыть всплывающее окно с кнопками
    await bot.answer_callback_query(callback_query_id)

    # Сбрасываем состояние
    await state.finish()

    # Отправляем сообщение об успешной рассылке
    await bot.send_message(message.from_user.id, "Рассылка успешно завершена.")

@dp.message_handler(lambda message: message.text == 'Мастера' and Admin.is_Admin(message.from_user.id))
async def admin_manage_masters(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    info_master_btn = types.KeyboardButton('Информация о мастерах')
    edit_master_btn = types.KeyboardButton('Изменить мастера')
    delete_master_btn = types.KeyboardButton('Удалить мастера')
    service_master_btn = types.KeyboardButton('Услуги мастера')
    back_btn = types.KeyboardButton('Назад')
    keyboard.add( info_master_btn, edit_master_btn, delete_master_btn, service_master_btn, back_btn)
    await bot.send_message(message.chat.id, "Выберите действие с мастерами:", reply_markup=keyboard)

def get_admin_data():
    cursor.execute("SELECT Name, Chat_id FROM Admin")
    admin_data = cursor.fetchone()
    return admin_data

def is_master_already_activated(master_chat_id):
    cursor.execute("SELECT * FROM Master WHERE Chat_id = ?", (master_chat_id,))
    return cursor.fetchone() is not None

@dp.message_handler(lambda message: message.text == 'Информация о мастерах' and Admin.is_Admin(message.from_user.id))
async def master_info_activation(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    spisok_master_btn = types.KeyboardButton('Список мастеров')
    dayoff_master_btn = types.KeyboardButton('Выходные мастеров')
    work_hour_master_btn = types.KeyboardButton('Рабочие часы мастеров')
    back_btn = types.KeyboardButton('Назад')
    keyboard.add( spisok_master_btn, dayoff_master_btn, work_hour_master_btn, back_btn)
    await bot.send_message(message.chat.id, "Какую информацию о мастерах вы хотите посмотреть", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == 'Список мастеров' and Admin.is_Admin(message.from_user.id))
async def master_spisok_activation(message: types.Message, state: FSMContext):
    # Получаем список всех мастеров из базы данных
    cursor.execute('SELECT * FROM Master')
    masters = cursor.fetchall()

    # Проверяем, есть ли мастры в базе данных
    if not masters:
        await message.answer("В базе данных нет зарегистрированных мастеров.")
        return

    # Формируем текст для сообщения со списком мастеров
    master_list_text = "Список мастеров:\n"
    for master in masters:
        master_list_text += f"{master[1]}\n"

    # Отправляем сообщение со списком мастеров
    await message.answer(master_list_text)

from datetime import datetime

@dp.message_handler(lambda message: message.text == 'Выходные мастеров' and Admin.is_Admin(message.from_user.id))
async def master_dayoff_activation(message: types.Message, state: FSMContext):
    # Получаем текущую дату
    current_date = datetime.now()

    # Получаем список всех мастеров из базы данных
    cursor.execute('SELECT * FROM Master')
    masters = cursor.fetchall()

    # Проверяем, есть ли мастры в базе данных
    if not masters:
        await message.answer("В базе данных нет зарегистрированных мастеров.")
        return

    # Проходим по каждому мастеру
    for master in masters:
        # Получаем выходные дни мастера, которые еще предстоят
        cursor.execute('SELECT * FROM DayOff WHERE Master = ? AND Year >= ? AND (Year > ? OR (Year = ? AND Month >= ?) OR (Year = ? AND Month = ? AND Day >= ?))',
                       (master[2], current_date.year, current_date.year, current_date.year, current_date.month, current_date.year, current_date.month, current_date.day))
        dayoffs = cursor.fetchall()

        # Проверяем, есть ли у мастера выходные дни
        if not dayoffs:
            await message.answer(f"Мастер {master[1]} не выбрал себе выходные дни.")
        else:
            # Формируем текст для сообщения со списком актуальных выходных дней мастера
            dayoff_list_text = f"Актуальные выходные дни мастера {master[1]}:\n"
            for dayoff in dayoffs:
                dayoff_list_text += f"{dayoff[4]}.{dayoff[3]}.{dayoff[2]}\n"

            # Отправляем сообщение со списком актуальных выходных дней мастера
            await message.answer(dayoff_list_text)

@dp.message_handler(lambda message: message.text == 'Рабочие часы мастеров')
async def work_hours_activation(message: types.Message, state: FSMContext):
    # Получаем список всех мастеров из базы данных
    cursor.execute('SELECT * FROM Master')
    masters = cursor.fetchall()

    # Проверяем, есть ли мастры в базе данных
    if not masters:
        await message.answer("В базе данных нет зарегистрированных мастеров.")
        return

    # Создаем клавиатуру для вывода часов каждого мастера
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    # Проходим по каждому мастеру
    for master in masters:
        # Получаем рабочие часы мастера
        cursor.execute(
            '''SELECT "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00" FROM WorkingHours WHERE Master=?''',
            (master[2],))
        work_hours = cursor.fetchone()

        # Проверяем, есть ли у мастера рабочие часы
        if work_hours:
            # Формируем текст для сообщения с рабочими часами мастера
            work_hours_text = f"Рабочие часы мастера {master[1]}:\n"
            # Проходим по каждому часу и добавляем в текст те, где значение True
            for hour, is_work_hour in zip(range(8, 20), work_hours):
                if is_work_hour:
                    work_hours_text += f"{hour:02d}:00 - {(hour + 1):02d}:00\n"

            # Добавляем кнопку с именем мастера в клавиатуру
            keyboard.add(KeyboardButton(f"Мастер: {master[1]}"))
            # Отправляем сообщение с рабочими часами мастера
            await message.answer(work_hours_text)
        else:
            # Если рабочих часов нет, выводим сообщение
            await message.answer(f"Мастер {master[1]} еще не выбрал рабочие часы.")


def is_admin_exist():
    cursor.execute("SELECT COUNT(*) FROM Admin")
    count = cursor.fetchone()[0]
    return count > 0




@dp.message_handler(lambda message: message.text == 'Я мастер')
async def handle_master_activation(message: types.Message, state: FSMContext):
    # Проверяем, является ли отправитель мастером
    master_chat_id = message.chat.id
    if not is_admin_exist():
        await bot.send_message(message.chat.id, "Данный бот еще на стадии заполнения базы, повторите попытку позже.")
        return
    # Сохраняем идентификатор чата мастера в mess_data
    mess_data['master_chat_id'] = master_chat_id
    # Очищаем данные из словаря


    master_chat_id = message.from_user.id
    message_id = message.message_id

    # Проверяем, активировал ли пользователь ключ
    if is_master_already_activated(master_chat_id):
            await bot.send_message(master_chat_id, "Вы уже активировали ключ.")
            return

    cursor.execute("INSERT INTO Key (Master, Massege_id) VALUES (?, ?)", (master_chat_id, message_id))
    conn.commit()
        # Отправляем уведомление пользователю
    await bot.send_message(master_chat_id, "Ваш запрос отправлен на обработку. Ожидайте подтверждения администратора.")

        # Получаем данные администратора
    admin_data = get_admin_data()

        # Отправляем уведомление администратору
    if admin_data:
            admin_name, admin_chat_id = admin_data
            keyboard = InlineKeyboardMarkup()
            allow_button = InlineKeyboardButton("Да", callback_data="allow_master_activation")
            deny_button = InlineKeyboardButton("Нет", callback_data="deny_master_activation")
            keyboard.add(allow_button, deny_button)
            sent_message = await bot.send_message(admin_chat_id,
                                                  f"Пользователь {message.from_user.username} активировал ключ мастера. Добавить мастера?",
                                                  reply_markup=keyboard)
            # Сохраняем идентификатор чата пользователя в состоянии
            await state.update_data(master_chat_id=master_chat_id)
            await state.update_data(sent_message_id=sent_message.message_id)


# Обработчик колбэков
@dp.callback_query_handler(lambda query: query.data in {"allow_master_activation", "deny_master_activation"})
async def handle_callback(call: CallbackQuery, state: FSMContext):
    # Получаем данные из состояния
    user_chat_id = mess_data['master_chat_id']
    admin_data = get_admin_data()
    admin_name, admin_chat_id = admin_data

    # Проверяем тип колбэка (Подтверждение или Отклонение)
    if call.data == "allow_master_activation":
        # Обновляем статус заявки на Подтверждено
        await bot.answer_callback_query(call.id, text="Заявка подтверждена")
        # Отправляем ответное сообщение пользователю
        await bot.send_message(user_chat_id, "Ваш запрос на статус мастера подтверждена, подождите пока придет подтверждение о добавлении вас в базу данных.")

        await process_add_master(types.Message(
            message_id=call.message.message_id,
            chat=types.Chat(id=admin_chat_id),
            text="Добавить мастера"
        ))

    elif call.data == "deny_master_activation":
        # Обновляем статус заявки на Отклонено
        await bot.answer_callback_query(call.id, text="Заявка отклонена")
        # Отправляем ответное сообщение пользователю
        await bot.send_message(user_chat_id, "Ваш запрос на статус мастера отклонен.")

    # Удаляем данные из состояния


    # Удаляем сообщение с кнопками у администратора
    await bot.delete_message(call.from_user.id, call.message.message_id)


@dp.message_handler(lambda message: message.text == 'Услуги мастера' and Admin.is_Admin(message.from_user.id))
async def admin_manage_mastersservice(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    add_smaster = types.KeyboardButton('Добавить услуги мастеру')
    delete_smaster_btn = types.KeyboardButton('Удалить услуги мастеру')

    # Добавляем две кнопки в клавиатуру
    keyboard.add(add_smaster, delete_smaster_btn)

    # Добавляем кнопку "Назад" в отдельный ряд
    back_btn = types.KeyboardButton('Назад')
    keyboard.add(back_btn)

    await bot.send_message(message.chat.id, "Выберите действие по работе с услугами предоставляемыми мастерами:", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == 'Услуги' and Admin.is_Admin(message.from_user.id))
async def admin_manage_services(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    add_service_btn = types.KeyboardButton('Добавить услугу')
    edit_service_btn = types.KeyboardButton('Изменить услугу')
    delete_service_btn = types.KeyboardButton('Удалить услугу')
    back_btn = types.KeyboardButton('Назад')
    keyboard.add(add_service_btn, edit_service_btn, delete_service_btn, back_btn)
    await bot.send_message(message.chat.id, "Выберите действие с услугами:", reply_markup=keyboard)


#######################################Добавление, редактирование и удаление мастеров от лица администратора

@dp.message_handler(lambda message: message.text == 'Добавить мастера' and Admin.is_Admin(message.from_user.id))
async def process_add_master(message: types.Message):
    await AddStates.waiting_for_name.set()  # Устанавливаем состояние ожидания имени мастера
    await bot.send_message(message.chat.id,
                           "Введите имя нового мастера:")  # Отправляем сообщение с запросом информации о новом мастере

@dp.message_handler(state=AddStates.waiting_for_name)
async def add_master_name(message: types.Message, state: FSMContext):
    # Получаем данные об администраторе
    admin_data = get_admin_data()
    admin_name, admin_chat_id = admin_data

    # Проверяем, что сообщение пришло от администратора
    if message.from_user.id != int(admin_chat_id):
        await message.answer("Вы не администратор. Доступ запрещен.")
        return

    # Обработка введенного имени мастера
    async with state.proxy() as data:
        data['name'] = message.text

    async with state.proxy() as data:
        user_chat_id = mess_data['master_chat_id']
    # Выполнение SQL-запроса для добавления информации в базу данных
    cursor.execute("INSERT INTO Master (Name, Chat_id) VALUES (?, ?)",
                   (data['name'], user_chat_id))
    conn.commit()

    # Получение списка услуг из базы данных
    services = cursor.execute("SELECT * FROM Service").fetchall()

    # Формирование inline клавиатуры с кнопками для каждой услуги
    keyboard = InlineKeyboardMarkup()
    for service in services:
        keyboard.add(InlineKeyboardButton(service[1], callback_data=f"add_service:{service[0]}"))

    keyboard.add(InlineKeyboardButton("Добавить", callback_data="confirm_add_services"))

    await message.answer("Выберите услуги для добавления:", reply_markup=keyboard)

    # Переключение на состояние ожидания подтверждения добавления услуг
    await AddStates.waiting_for_service_confirmation.set()


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('add_service:'), state=AddStates.waiting_for_service_confirmation)
async def add_service_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Получение данных из callback_data
    service_id = int(callback_query.data.split(":")[1])

    # Проверка, была ли уже выбрана данная услуга
    selected_services = await state.get_data()
    if service_id in selected_services.get('services', []):
        await callback_query.answer("Услуга уже выбрана")
    else:
        # Добавление выбранной услуги в состояние
        selected_services.setdefault('services', []).append(service_id)
        await state.update_data(selected_services)
        await callback_query.answer(f"Услуга добавлена: {callback_query.message.text}")


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'confirm_add_services', state=AddStates.waiting_for_service_confirmation)
async def confirm_add_services(callback_query: types.CallbackQuery, state: FSMContext):
    # Получение выбранных услуг из состояния
    selected_services = await state.get_data()
    selected_services = selected_services.get('services', [])

    # Получение ID последнего добавленного мастера
    master_id = cursor.execute("SELECT MAX(ID) FROM Master").fetchone()[0]

    # Вставка выбранных услуг в базу данных
    values = [(master_id, service_id) for service_id in selected_services]
    cursor.executemany("INSERT INTO MasterService (MasterID, ServiceID) VALUES (?, ?)", values)
    conn.commit()

    # Сброс состояния
    await state.finish()

    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id,
                                text="Услуги успешно добавлены")
    user_chat_id = mess_data['master_chat_id']
    reboot_button = types.KeyboardButton('Перезапустить бота')

    # Создаем клавиатуру с одной кнопкой
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(reboot_button)
    await bot.send_message(user_chat_id, "Вас внесли в базу данных, можете перезапустить бота", reply_markup=keyboard)

# Обработчик нажатия на кнопку
@dp.message_handler(lambda message: message.text == 'Перезапустить бота' and Master.is_Master(message.from_user.id))
async def handle_reboot_button(message: types.Message):
    # Удаление клавиатуры
    master_chat_id= mess_data['master_chat_id']
    await bot.send_message(master_chat_id, "Бот перезапускается...")
    await bot.send_chat_action(master_chat_id, "typing")  # Эмулируем действие набора сообщения
    await asyncio.sleep(1)  # Ждем некоторое время (может потребоваться настройка)
    await process_start_command(message)



@dp.message_handler(lambda message: message.text == 'Изменить мастера' and Admin.is_Admin(message.from_user.id))
async def edit_master_callback(message: types.Message, state: FSMContext):
    # Получение списка всех мастеров
    masters = cursor.execute("SELECT * FROM Master").fetchall()

    if not masters:
        await bot.send_message(message.chat.id, "Нет доступных мастеров для изменения.")
        return

    # Создаем инлайн-клавиатуру с кнопками для каждого мастера
    keyboard = types.InlineKeyboardMarkup()
    for master in masters:
        master_id = master[0]
        master_name = master[1]
        chat_id = master[2]
        button_text = f"Изменить {master_name} (ID чата: {chat_id})"
        button_callback = f"edit_master_{master_id}"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=button_callback))

    # Отправляем сообщение с инлайн-клавиатурой
    edit_message = await bot.send_message(message.chat.id, "Выберите мастера для изменения:", reply_markup=keyboard)

    # Обновляем состояние для отслеживания последнего отправленного сообщения
    await state.update_data(edit_message_id=edit_message.message_id)
    await state.update_data(chosen_master_id=None)

@dp.callback_query_handler(lambda query: query.data.startswith("edit_master"), state="*")
async def edit_master_callback(query: types.CallbackQuery, state: FSMContext):
    chosen_master_id = int(query.data.split('_')[2])
    # Сохраняем ID выбранного мастера в состоянии
    await state.update_data(chosen_master_id=chosen_master_id)

    # Отправляем запрос администратору для выбора, что он хочет изменить
    await bot.edit_message_text("Что вы хотите изменить?",
                               chat_id=query.message.chat.id,
                               message_id=(await state.get_data())["edit_message_id"],
                               reply_markup=InlineKeyboardMarkup(row_width=1, inline_keyboard=[
                                   [InlineKeyboardButton("Имя", callback_data="edit_name")],
                                   [InlineKeyboardButton("ID чата", callback_data="edit_chat_id")],
                                   [InlineKeyboardButton("Изменить все", callback_data="edit_all")],
                               ]))

    # Переключаемся в состояние ожидания выбора действия
    await EditStates.waiting_for_edit_choice.set()


@dp.callback_query_handler(lambda query: query.data in {"edit_name", "edit_chat_id", "edit_all"},
                           state=EditStates.waiting_for_edit_choice)
async def edit_master_callback(query: types.CallbackQuery, state: FSMContext):
    data = {"edit_choice": query.data}

    # Сохраняем выбор администратора в состоянии
    await state.update_data(data)

    if query.data == "edit_name":
        # Переключаемся в состояние ожидания нового имени мастера
        await EditStates.waiting_for_new_name.set()
        await bot.edit_message_text("Введите новое имя мастера:", chat_id=query.message.chat.id,
                                    message_id=query.message.message_id)
    elif query.data == "edit_chat_id":
        # Переключаемся в состояние ожидания нового ID чата мастера
        await EditStates.waiting_for_new_chat_id.set()
        await bot.edit_message_text("Введите новый ID чата мастера:", chat_id=query.message.chat.id,
                                    message_id=query.message.message_id)
    elif query.data == "edit_all":
        # Переключаемся в состояние ожидания нового имени
        await EditStates.waiting_for_new_name.set()
        await bot.edit_message_text("Введите новое имя мастера:", chat_id=query.message.chat.id,
                                    message_id=query.message.message_id)


@dp.message_handler(state=EditStates.waiting_for_new_chat_id)
async def edit_master_new_chat_id(message: types.Message, state: FSMContext):
    chosen_master_id = (await state.get_data())["chosen_master_id"]
    edit_choice = (await state.get_data())["edit_choice"]

    # Проверяем, есть ли ключ "new_name" в данных состояния
    new_name = (await state.get_data()).get("new_name")

    new_chat_id = message.text

    # В зависимости от выбора администратора выполняем соответствующий запрос в базу данных
    if edit_choice == "edit_name":
        update_name_in_db(cursor, chosen_master_id, new_name)
    elif edit_choice == "edit_chat_id":
        update_chat_id_in_db(cursor, chosen_master_id, new_chat_id)
    elif edit_choice == "edit_all":
        # Если выбрано "Изменить все", обновляем и имя, и ID чата
        update_name_in_db(cursor, chosen_master_id, new_name)
        update_chat_id_in_db(cursor, chosen_master_id, new_chat_id)

    conn.commit()

    # Сбрасываем состояние
    await state.reset_state()

    await bot.send_message(message.chat.id, "Информация успешно обновлена")

@dp.message_handler(state=EditStates.waiting_for_new_name)
async def edit_master_new_name(message: types.Message, state: FSMContext):
    chosen_master_id = (await state.get_data())["chosen_master_id"]
    edit_choice = (await state.get_data())["edit_choice"]
    new_name = message.text

    # В зависимости от выбора администратора выполняем соответствующий запрос в базу данных
    if edit_choice == "edit_name":
        update_name_in_db(cursor, chosen_master_id, new_name)

    elif edit_choice == "edit_chat_id":
        # Если выбрано изменение ID чата, сохраняем новое имя в состоянии для дальнейшего использования
        await state.update_data(new_name=new_name)
        # Переключаемся в состояние ожидания нового ID чата мастера
        await EditStates.waiting_for_new_chat_id.set()
        await bot.send_message(message.chat.id, "Введите новый ID чата мастера:")
        return
    elif edit_choice == "edit_all":
        # Если выбрано "Изменить все", сохраняем новое имя в состоянии для дальнейшего использования
        await state.update_data(new_name=new_name)
        # Переключаемся в состояние ожидания нового ID чата мастера
        await EditStates.waiting_for_new_chat_id.set()
        await bot.send_message(message.chat.id, "Введите новый ID чата мастера:")
        return

    conn.commit()

    # Сбрасываем состояние
    await state.reset_state()

    await bot.send_message(message.chat.id, "Информация успешно обновлена")


@dp.message_handler(lambda message: message.text == 'Удалить мастера' and Admin.is_Admin(message.from_user.id))
async def delete_master_callback(message: types.Message, state: FSMContext):
    # Получение списка всех мастеров
    masters = cursor.execute("SELECT * FROM Master").fetchall()

    if not masters:
        await bot.send_message(message.chat.id, "Нет доступных мастеров для удаления.")
        return

    # Создаем инлайн-клавиатуру с кнопками для каждого мастера
    keyboard = types.InlineKeyboardMarkup()
    for master in masters:
        master_id = master[0]
        master_name = master[1]
        button_text = f"Удалить {master_name}"
        button_callback = f"delete_master_{master_id}"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=button_callback))

    # Отправляем сообщение с инлайн-клавиатурой
    await bot.send_message(message.chat.id, "Выберите мастера для удаления:", reply_markup=keyboard)

    # Переключаемся в состояние ожидания выбора мастера для удаления
    await DeleteStates.waiting_for_master_choice.set()

@dp.callback_query_handler(lambda query: query.data.startswith("delete_master"), state=DeleteStates.waiting_for_master_choice)
async def delete_master_confirmation_callback(query: types.CallbackQuery, state: FSMContext):
    chosen_master_id = int(query.data.split('_')[2])
    # Сохраняем ID выбранного мастера в состоянии
    await state.update_data(chosen_master_id=chosen_master_id)

    # Получаем имя мастера для подтверждения удаления
    master_name = cursor.execute("SELECT Name FROM Master WHERE ID = ?", (chosen_master_id,)).fetchone()[0]

    # Отправляем сообщение с вопросом об удалении и кнопками "Да" и "Нет"
    await bot.edit_message_text(
        f"Вы точно хотите удалить мастера {master_name}?",
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        reply_markup=InlineKeyboardMarkup(row_width=2, inline_keyboard=[
            [InlineKeyboardButton("Да", callback_data="confirm_delete"), InlineKeyboardButton("Нет", callback_data="cancel_delete")],
        ]))

    # Переключаемся в состояние ожидания подтверждения удаления
    await DeleteStates.waiting_for_confirmation.set()

# ...

@dp.callback_query_handler(lambda query: query.data in {"confirm_delete", "cancel_delete"}, state=DeleteStates.waiting_for_confirmation)
async def delete_master(query: types.CallbackQuery, state: FSMContext):
    # Получаем данные из состояния
    chosen_master_id = (await state.get_data())["chosen_master_id"]
    confirmation = query.data == "confirm_delete"

    if confirmation:
        # Получаем chat_id мастера
        cursor.execute("SELECT Chat_id FROM Master WHERE ID = ?", (chosen_master_id,))
        chat_id_result = cursor.fetchone()
        if chat_id_result:
            chat_id = chat_id_result[0]

            # Проверяем наличие записей в таблице WorkingHours
            cursor.execute("SELECT * FROM WorkingHours WHERE Master = ?", (chat_id,))
            working_hours_result = cursor.fetchone()
            if working_hours_result:
                # Если есть записи, удаляем их
                cursor.execute("DELETE FROM WorkingHours WHERE Master = ?", (chat_id,))
                conn.commit()

            # Проверяем наличие записей в таблице DayOff
            cursor.execute("SELECT * FROM DayOff WHERE Master = ?", (chat_id,))
            day_off_result = cursor.fetchone()
            if day_off_result:
                # Если есть записи, удаляем их
                cursor.execute("DELETE FROM DayOff WHERE Master = ?", (chat_id,))
                conn.commit()

            # Удаляем мастера из таблицы Master
            cursor.execute("DELETE FROM Master WHERE ID = ?", (chosen_master_id,))
            conn.commit()

            await bot.edit_message_text("Мастер успешно удален.", chat_id=query.message.chat.id,
                                        message_id=query.message.message_id)
        else:
            await bot.edit_message_text("Ошибка: не удалось найти chat_id мастера.", chat_id=query.message.chat.id,
                                        message_id=query.message.message_id)
    else:
        await bot.edit_message_text("Удаление отменено.", chat_id=query.message.chat.id,
                                    message_id=query.message.message_id)

    # Сбрасываем состояние
    await state.reset_state()
    
@dp.message_handler(lambda message: message.text == 'Удалить услуги мастеру' and Admin.is_Admin(message.from_user.id))
async def admin_manage_dellmastersservice(message: types.Message, state: FSMContext):
    # Получаем список мастеров
    cursor.execute('SELECT * FROM Master')
    masters = cursor.fetchall()

    # Формируем inline-кнопки для выбора мастера
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for master in masters:
        keyboard.add(types.InlineKeyboardButton(text=master[1], callback_data=f'master_{master[0]}'))

    # Отправляем сообщение с inline-кнопками мастеров
    await message.answer("Выберите мастера для удаления услуги:", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('master_'))
async def choose_master_for_service_deletion(callback_query: types.CallbackQuery):
    master_id = int(callback_query.data.split('_')[1])

    # Получаем услуги мастера
    cursor.execute('''
        SELECT s.ID, s.Name
        FROM MasterService ms
        JOIN Service s ON ms.ServiceID = s.ID
        WHERE ms.MasterID = ?
    ''', (master_id,))
    services = cursor.fetchall()

    # Формируем inline-кнопки для выбора услуги
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for service in services:
        keyboard.add(types.InlineKeyboardButton(text=service['Name'], callback_data=f'service_{service["ID"]}'))

    # Отправляем сообщение с inline-кнопками услуг мастера
    await callback_query.message.edit_text("Выберите услугу для удаления:", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith('service_'))
async def delete_service(callback_query: types.CallbackQuery):
    service_id = int(callback_query.data.split('_')[1])

    # Удаляем запись из таблицы MasterService по выбранной услуге
    cursor.execute('DELETE FROM MasterService WHERE ServiceID = ?', (service_id,))
    conn.commit()

    # Отправляем сообщение об успешном удалении
    await callback_query.message.answer("Услуга успешно удалена")




@dp.message_handler(lambda message: message.text == 'Добавить услуги мастеру' and Admin.is_Admin(message.from_user.id))
async def admin_manage_addmastersservice(message: types.Message, state: FSMContext):
    # Получение списка всех мастеров
    masters = cursor.execute("SELECT * FROM Master").fetchall()
    if not masters:
        await bot.send_message(message.chat.id, "Нет доступных мастеров для добавления.")
        return

    # Создаем инлайн-клавиатуру с кнопками для каждого мастера
    keyboard = types.InlineKeyboardMarkup()
    for master in masters:
        master_id = master[0]
        master_name = master[1]
        button_text = f"{master_name}"
        button_callback = f"addservice_master_{master_id}"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=button_callback))

    await bot.send_message(message.chat.id, "Выберите мастера для добавления услуг:", reply_markup=keyboard)


@dp.callback_query_handler(lambda query: query.data.startswith("addservice_master_"))
async def handle_add_service_to_master(query: types.CallbackQuery, state: FSMContext):
    master_id = int(query.data.split('_')[2])

    # Получение списка ServiceID, которые уже выполняет мастер
    master_services = cursor.execute("SELECT ServiceID FROM MasterService WHERE MasterID = ?", (master_id,)).fetchall()
    existing_service_ids = [service[0] for service in master_services]

    # Получение списка всех доступных услуг, исключая те, которые уже выполняет мастер
    services = cursor.execute(
        "SELECT * FROM Service WHERE ID NOT IN ({})".format(', '.join(map(str, existing_service_ids)))).fetchall()

    if not services:
        await bot.edit_message_text("Нет доступных услуг для добавления.", chat_id=query.message.chat.id,
                                    message_id=query.message.message_id)
        return

    # Создаем инлайн-клавиатуру с кнопками для каждой услуги
    keyboard = InlineKeyboardMarkup()
    for service in services:
        keyboard.add(InlineKeyboardButton(service[1], callback_data=f"confirm_add_service:{service[0]}:{master_id}"))

    keyboard.add(InlineKeyboardButton("Добавить", callback_data=f"add_add_services:{master_id}"))
    await bot.edit_message_text("Выберите услуги для добавления:", chat_id=query.message.chat.id,
                                message_id=query.message.message_id, reply_markup=keyboard)

    await AddMasterService.waiting_for_masterservice_confirmation.set()


@dp.callback_query_handler(lambda query: query.data.startswith("confirm_add_service:"), state=AddMasterService.waiting_for_masterservice_confirmation)
async def confirm_add_services(query: types.CallbackQuery, state: FSMContext):
    # Получение данных из callback_data
    service_id = int(query.data.split(":")[1])
    master_id = int(query.data.split(":")[2])

    # Проверка, была ли уже выбрана данная услуга
    selected_masterservices = await state.get_data()
    if service_id in selected_masterservices.get('masterservices', []):
        await query.answer("Услуга уже выбрана")
    else:
        # Добавление выбранной услуги в состояние
        selected_masterservices.setdefault('masterservices', []).append(service_id)
        await state.update_data(selected_masterservices)
        await query.answer(f"Услуга добавлена: {query.message.text}")

@dp.callback_query_handler(lambda query: query.data.startswith("add_add_services:"), state=AddMasterService.waiting_for_masterservice_confirmation)
async def handle_add_services_confirmation(query: types.CallbackQuery, state: FSMContext):
    # Получение выбранных услуг из состояния
    selected_masterservices = await state.get_data()
    selected_masterservices = selected_masterservices.get('masterservices', [])

    master_id = int(query.data.split(":")[1])

    # Вставка выбранных услуг в базу данных
    for service_id in selected_masterservices:
        # Проверяем, существует ли уже такая комбинация MasterID и ServiceID
        existing_record = cursor.execute("SELECT * FROM MasterService WHERE MasterID = ? AND ServiceID = ?", (master_id, service_id)).fetchone()
        if not existing_record:
            cursor.execute("INSERT INTO MasterService (MasterID, ServiceID) VALUES (?, ?)", (master_id, service_id))
            conn.commit()

    # Сброс состояния
    await state.finish()


    await bot.edit_message_text(chat_id=query.message.chat.id,
                                message_id=query.message.message_id,
                                text="Услуги успешно добавлены")






#######################################Добавление, редактирование и удаление услуг от лица администратора


@dp.message_handler(lambda message: message.text == "Добавить услугу" and Admin.is_Admin(message.from_user.id))
async def process_add_service(message: types.Message):
    await add_Service(message)

@dp.message_handler(state=AddStates.waiting_for_servicename)
async def add_service_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['servicename'] = message.text
    await AddStates.waiting_for_servicetime.set()

    # Создаем инлайн-клавиатуру для выбора времени
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("1 час", callback_data="new_time_1"),
        InlineKeyboardButton("2 часа", callback_data="new_time_2")
    )

    await message.answer("Выберите время затрачиваемое на услугу:", reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data.startswith("new_time"), state=AddStates.waiting_for_servicetime)
async def handle_new_time_callback(query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        time=query.data.split("_")[-1]
        if time == "1":
            data['servicetime'] = "1 час"
        else:
            data['servicetime'] = "2 часа"

    await AddStates.waiting_for_serviceprice.set()
    await bot.edit_message_text("Введите цену услуги в рублях:", chat_id=query.message.chat.id,
                                message_id=query.message.message_id)

@dp.message_handler(state=AddStates.waiting_for_serviceprice)
async def add_service_price(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        # Проверяем, что введенная строка состоит только из цифр
        if not message.text.isdigit():
            await message.answer("Введите корректную цену. Она должна состоять только из цифр.")
            return

        data['serviceprice'] = int(message.text)

    # Выполнение SQL-запроса для добавления информации в базу данных
    cursor.execute("INSERT INTO Service (Name, Time, Price) VALUES (?, ?, ?)",
                   (data['servicename'], data['servicetime'], data['serviceprice']))
    conn.commit()

    await state.reset_state()  # Сброс состояния
    # Редактируем изначальное сообщение
    await message.answer("Информация успешно добавлена")


@dp.message_handler(lambda message: message.text == 'Изменить услугу' and Admin.is_Admin(message.from_user.id))
async def edit_service_callback(message: types.Message, state: FSMContext):
    # Получение списка всех услуг
    services = cursor.execute("SELECT * FROM Service").fetchall()

    if not services:
        await bot.send_message(message.chat.id, "Нет доступных услуг для изменения.")
        return

    # Создаем инлайн-клавиатуру с кнопками для каждой услуги
    keyboard = types.InlineKeyboardMarkup()
    for service in services:
        service_id = service[0]
        service_name = service[1]
        service_time = service[2]
        service_price = service[3]
        button_text = f"{service_name}"
        button_callback = f"edit_service_{service_id}"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=button_callback))

    # Отправляем сообщение с инлайн-клавиатурой
    edit_message = await bot.send_message(message.chat.id, "Выберите услугу для изменения:", reply_markup=keyboard)

    # Обновляем состояние для отслеживания последнего отправленного сообщения
    await state.update_data(edit_message_id=edit_message.message_id)
    await state.update_data(chosen_service_id=None)

@dp.callback_query_handler(lambda query: query.data.startswith("edit_service"), state="*")
async def edit_service_callback(query: types.CallbackQuery, state: FSMContext):
    chosen_service_id = int(query.data.split('_')[2])

    # Сохраняем ID выбранного мастера в состоянии
    await state.update_data(chosen_service_id=chosen_service_id)

    # Отправляем запрос администратору для выбора, что он хочет изменить
    await bot.edit_message_text("Что вы хотите изменить?",
                               chat_id=query.message.chat.id,
                               message_id=(await state.get_data())["edit_message_id"],
                               reply_markup=InlineKeyboardMarkup(row_width=1, inline_keyboard=[
                                   [InlineKeyboardButton("Наименование", callback_data="edit_names")],
                                   [InlineKeyboardButton("Время услуги", callback_data="edit_time_service")],
                                   [InlineKeyboardButton("Цену услуги", callback_data="edit_price")],
                                   [InlineKeyboardButton("Изменить все", callback_data="edit_allservice")],
                               ]))

    # Переключаемся в состояние ожидания выбора действия
    await EditServiceStates.edit_choice.set()

@dp.callback_query_handler(lambda query: query.data == "edit_names", state=EditServiceStates.edit_choice)
async def edit_names_callback(query: types.CallbackQuery, state: FSMContext):
    data = {"edit_choices": query.data}
    await state.update_data(data)

    await EditServiceStates.new_name.set()
    await bot.edit_message_text("Введите новое наименование услуги: ", chat_id=query.message.chat.id,
                                message_id=query.message.message_id)

@dp.callback_query_handler(lambda query: query.data == "edit_price", state=EditServiceStates.edit_choice)
async def edit_price_callback(query: types.CallbackQuery, state: FSMContext):
    data = {"edit_choices": query.data}
    await state.update_data(data)

    await EditServiceStates.new_price.set()
    await bot.edit_message_text("Введите новую цену услуги: ", chat_id=query.message.chat.id,
                                message_id=query.message.message_id)

@dp.callback_query_handler(lambda query: query.data == "edit_time_service", state=EditServiceStates.edit_choice)
async def edit_time_service_callback(query: types.CallbackQuery, state: FSMContext):
    data = {"edit_choices": query.data}
    await state.update_data(data)

    await EditServiceStates.new_time.set()
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("1 час", callback_data="new_time_1"),
        InlineKeyboardButton("2 часа", callback_data="new_time_2")
    )
    await bot.edit_message_text("Выберите новое время услуги:", chat_id=query.message.chat.id,
                                message_id=query.message.message_id, reply_markup=keyboard)

@dp.callback_query_handler(lambda query: query.data == "edit_allservice", state=EditServiceStates.edit_choice)
async def edit_allservice_callback(query: types.CallbackQuery, state: FSMContext):
    data = {"edit_choices": query.data}
    await state.update_data(data)

    await EditServiceStates.new_name.set()
    await bot.edit_message_text("Введите новое наименование услуги: ", chat_id=query.message.chat.id,
                                message_id=query.message.message_id)



@dp.callback_query_handler(lambda query: query.data.startswith("new_time"), state=EditServiceStates.new_time)
async def handle_new_time_callback(query: types.CallbackQuery, state: FSMContext):
    chosen_service_id = (await state.get_data())["chosen_service_id"]
    edit_choice = (await state.get_data())["edit_choices"]

    # Проверяем, есть ли ключ "new_name" в данных состояния
    new_names = (await state.get_data()).get("new_names")

    new_times = query.data.split("_")[-1]
    if new_times == "1":
        new_time = "1 час"
    else:
        new_time = "2 часа"


    # Сохраняем выбранное время в переменной состояния
    await state.update_data(new_time=new_times)

    # В зависимости от выбора администратора выполняем соответствующий запрос в базу данных
    if edit_choice == "edit_time_service":
        update_time_in_db(cursor, chosen_service_id, new_times)
        conn.commit()

        # Сбрасываем состояние
        await state.reset_state()
        # Редактируем изначальное сообщение
        await bot.edit_message_text("Информация успешно обновлена", chat_id=query.message.chat.id,
                                    message_id=query.message.message_id)

    elif edit_choice == "edit_allservice":
        # Если выбрано "Изменить все", обновляем и имя, и ID чата
        update_nameservice_in_db(cursor, chosen_service_id, new_names)
        update_time_in_db(cursor, chosen_service_id, new_time)
        await EditServiceStates.new_price.set()
        await bot.edit_message_text("Введите новую цену услуги: ", chat_id=query.message.chat.id,
                                    message_id=query.message.message_id)


@dp.message_handler(state=EditServiceStates.new_name)
async def edit_service_new_name(message: types.Message, state: FSMContext):
    chosen_service_id = (await state.get_data())["chosen_service_id"]
    edit_choice = (await state.get_data())["edit_choices"]
    new_names = message.text

    # В зависимости от выбора администратора выполняем соответствующий запрос в базу данных
    if edit_choice == "edit_names":
        update_nameservice_in_db(cursor, chosen_service_id, new_names)

    elif edit_choice == "edit_allservice":
        # Если выбрано "Изменить все", сохраняем новое имя в состоянии для дальнейшего использования
        await state.update_data(new_name=new_names)
        # Переключаемся в состояние ожидания нового ID чата мастера
        update_nameservice_in_db(cursor, chosen_service_id, new_names)
        await EditServiceStates.new_time.set()
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("1 час", callback_data="new_time_1"),
            InlineKeyboardButton("2 часа", callback_data="new_time_2")
        )
        await bot.send_message(message.chat.id, "Выберите новое время услуги:", reply_markup=keyboard)

        return
    conn.commit()

    # Сбрасываем состояние
    await state.reset_state()

    await bot.send_message(message.chat.id, "Информация успешно обновлена")

@dp.message_handler(state=EditServiceStates.new_price)
async def edit_service_new_price(message: types.Message, state: FSMContext):
    chosen_service_id = (await state.get_data())["chosen_service_id"]
    edit_choice = (await state.get_data())["edit_choices"]
    new_price = message.text
    new_names = (await state.get_data()).get("new_names")
    new_time = (await state.get_data()).get("new_times")

    # В зависимости от выбора администратора выполняем соответствующий запрос в базу данных
    if edit_choice == "edit_price":
        update_price_in_db(cursor, chosen_service_id, new_price)
        await bot.send_message(message.chat.id, "Информация успешно обновлена")
        await state.reset_state()
        conn.commit()
    elif edit_choice == "edit_allservice":
        # Если выбрано "Изменить все", обновляем и имя, и ID чата
        update_nameservice_in_db(cursor, chosen_service_id, new_names)
        update_time_in_db(cursor, chosen_service_id, new_time)
        update_price_in_db(cursor, chosen_service_id, new_price)
        await EditServiceStates.new_price.set()
        await bot.send_message(message.chat.id, "Информация успешно обновлена")
        await state.reset_state()
        conn.commit()


    # Сбрасываем состояние


@dp.message_handler(lambda message: message.text == 'Удалить услугу' and Admin.is_Admin(message.from_user.id))
async def delete_service_callback(message: types.Message, state: FSMContext):
    # Получение списка всех мастеров
    services = cursor.execute("SELECT * FROM Service").fetchall()

    if not services:
        await bot.send_message(message.chat.id, "Нет доступных услуг для удаления.")
        return

    # Создаем инлайн-клавиатуру с кнопками для каждого мастера
    keyboard = types.InlineKeyboardMarkup()
    for service in services:
        service_id = service[0]
        service_name = service[1]
        button_text = f"Удалить {service_name}"
        button_callback = f"delete_service_{service_id}"
        keyboard.add(types.InlineKeyboardButton(button_text, callback_data=button_callback))

    # Отправляем сообщение с инлайн-клавиатурой
    await bot.send_message(message.chat.id, "Выберите услугу для удаления:", reply_markup=keyboard)

    # Переключаемся в состояние ожидания выбора мастера для удаления
    await DeleteStates.waiting_for_service_choice.set()


# ...

@dp.callback_query_handler(lambda query: query.data.startswith("delete_service"),
                           state=DeleteStates.waiting_for_service_choice)
async def delete_service_confirmation_callback(query: types.CallbackQuery, state: FSMContext):
    chosen_service_id = int(query.data.split('_')[2])
    # Сохраняем ID выбранной услуги в состоянии
    await state.update_data(chosen_service_id=chosen_service_id)

    # Получаем имя услуги для подтверждения удаления
    service_name = cursor.execute("SELECT Name FROM Service WHERE ID = ?", (chosen_service_id,)).fetchone()[0]

    # Отправляем сообщение с вопросом об удалении и кнопками "Да" и "Нет"
    await bot.edit_message_text(
        f"Вы точно хотите удалить услугу {service_name}?",
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        reply_markup=InlineKeyboardMarkup(row_width=2, inline_keyboard=[
            [InlineKeyboardButton("Да", callback_data="confirm_delete"),
             InlineKeyboardButton("Нет", callback_data="cancel_delete")],
        ]))

    # Переключаемся в состояние ожидания подтверждения удаления
    await DeleteStates.waiting_for_serevice.set()


# ...

@dp.callback_query_handler(lambda query: query.data in {"confirm_delete", "cancel_delete"},
                           state=DeleteStates.waiting_for_serevice)
async def delete_service(query: types.CallbackQuery, state: FSMContext):
    # Получаем данные из состояния
    chosen_service_id = (await state.get_data())["chosen_service_id"]
    confirmation = query.data == "confirm_delete"

    if confirmation:
        # Если подтверждено удаление, удаляем мастера
        cursor.execute("DELETE FROM Service WHERE ID = ?", (chosen_service_id,))

        # Удаляем записи из таблицы MasterService, связанные с удаляемой услугой
        cursor.execute("DELETE FROM MasterService WHERE ServiceID = ?", (chosen_service_id,))

        conn.commit()
        await bot.edit_message_text("Услуга успешно удалена.", chat_id=query.message.chat.id,
                                    message_id=query.message.message_id)
    else:
        await bot.edit_message_text("Удаление отменено.", chat_id=query.message.chat.id,
                                    message_id=query.message.message_id)

    # Сбрасываем состояние
    await state.reset_state()


###############################################################################Мастер
@dp.message_handler(lambda message: message.text == 'Мои заявки' and Master.is_Master(message.from_user.id))
async def master_records(message: types.Message):
    master_chat_id = message.from_user.id

    cursor.execute('''SELECT Record.*, Users.RealName, Service.Name, Service.Price, Service.Time 
                           FROM Record 
                           INNER JOIN Users ON Record.Client = Users.Chat_id 
                           INNER JOIN Service ON Record.Service = Service.ID
                           WHERE Record.Master=? AND Record.Pay=?''', (master_chat_id, True))
    records = cursor.fetchall()


    current_date = datetime.now().replace(microsecond=0)
    current_appointments = []

    for record in records:
        # Преобразуем текстовые значения в целочисленные
        record_year = int(record[6])
        record_month = int(record[7])
        record_day = int(record[9])

        # Преобразуем время из строки в объект datetime
        record_time = datetime.strptime(record[10], "%H:%M").time()
        record_hour = int(record_time.strftime("%H"))
        record_minute = int(record_time.strftime("%M"))
        record_date = datetime(record_year, record_month, record_day, record_hour, record_minute)

        # Проверяем, актуальна ли запись
        if current_date < record_date:
            current_appointments.append(record)

    if current_appointments:
        # Если есть актуальные записи, формируем сообщение с информацией по актуальным записям
        appointments_message = "Ваши актуальные заявки:\n\n"
        for record in current_appointments:
            appointment_info = f"Клиент: {record[13]}\nТелефон: {record[4]}\nУслуга: {record[14]}\nДата: {record[9]}.{record[7]}.{record[6]}\nВремя: {record[10]}\nЦена: {record[15]}\nДлительность: {record[16]}\n\n"
            appointments_message += appointment_info

        # Отправляем сообщение с информацией о записях
        await message.answer(appointments_message)
    else:
        # Если у пользователя нет актуальных записей, отправляем сообщение об этом
        await message.answer("У вас пока нет актуальных записей.")

@dp.message_handler(lambda message: message.text == 'Мои часы' and Master.is_Master(message.from_user.id))
async def masterhours(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    my_hours_btn = types.KeyboardButton('Выбранные часы')
    add_hours_btn = types.KeyboardButton('Добавить рабочие часы')
    delete_hours_btn = types.KeyboardButton('Удалить рабочие часы')
    back_btn = types.KeyboardButton('Назад')
    keyboard.add(my_hours_btn, add_hours_btn,  delete_hours_btn, back_btn)
    await bot.send_message(message.chat.id, "Выберите действие с часами:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == 'Добавить рабочие часы' and Master.is_Master(message.from_user.id))
async def add_working_hours(message: types.Message):

    # Получение текущего статуса часов для конкретного мастера
    cursor.execute('SELECT * FROM WorkingHours WHERE Master = ?', (str(message.from_user.id),))
    result = cursor.fetchone()

    # Создаем кнопки только для тех часов, где статус равен False
    working_hours = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for hour in working_hours:
        if not result or not result[working_hours.index(hour) + 2]:  # Индекс 2 соответствует столбцам с часами в таблице
            keyboard.add(types.KeyboardButton(hour))

    back_btn = types.KeyboardButton('Назад')
    keyboard.add(back_btn)


    await bot.send_message(message.chat.id, "Выберите рабочие часы для добавления:", reply_markup=keyboard)



@dp.message_handler(lambda message: message.text in ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
                                    and Master.is_Master(message.from_user.id) and not message.text.endswith("(удалить)"))
async def process_add_hours(message: types.Message):
    chat_id = message.chat.id
    selected_hour = message.text

    # Проверяем, существует ли уже запись для данного мастера
    cursor.execute('SELECT * FROM WorkingHours WHERE Master=?', (chat_id,))
    existing_record = cursor.fetchone()

    if existing_record:
        # Если запись существует, обновляем существующий час в соответствии с выбором мастера
        cursor.execute(f'''
            UPDATE WorkingHours
            SET "{selected_hour}" = ?
            WHERE Master = ?
        ''', (True, chat_id))
    else:
        # Если запись не существует, создаем новую запись для мастера
        cursor.execute(f'''
            INSERT INTO WorkingHours (Master, "{selected_hour}")
            VALUES (?, ?)
        ''', (chat_id, True))

    # Сохраняем изменения в базе данных
    conn.commit()
    # Обновляем кнопки после изменений в базе данных

    await bot.send_message(message.chat.id, f"Рабочие часы {selected_hour} успешно добавлены!")
    await update_keyboard(message)

async def update_keyboard(message: types.Message):
    # Получаем текущий статус часов для конкретного мастера
    cursor.execute('SELECT * FROM WorkingHours WHERE Master = ?', (str(message.from_user.id),))
    result = cursor.fetchone()

    # Создаем кнопки только для тех часов, где статус равен False
    working_hours = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for hour in working_hours:
        if not result or not result[working_hours.index(hour) + 2]:  # Индекс 2 соответствует столбцам с часами в таблице
            keyboard.add(types.KeyboardButton(hour))

    back_btn = types.KeyboardButton('Назад')
    keyboard.add(back_btn)

    await bot.send_message(message.chat.id, "Выберите рабочие часы для добавления:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == 'Удалить рабочие часы' and Master.is_Master(message.from_user.id))
async def delete_working_hours(message: types.Message):
    # Получаем текущий статус часов для конкретного мастера
    cursor.execute('SELECT * FROM WorkingHours WHERE Master = ?', (str(message.from_user.id),))
    result = cursor.fetchone()

    # Проверка наличия часов у мастера
    if not result or not any(result[2:]):
        await bot.send_message(message.chat.id, "У вас нет рабочих часов.")
        await process_start_command(message)
        return

    # Создаем кнопки только для тех часов, где статус равен True
    working_hours = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for hour in working_hours:
        if result and result[working_hours.index(hour) + 2]:  # Индекс 2 соответствует столбцам с часами в таблице
            keyboard.add(types.KeyboardButton(f"{hour} (удалить)"))

    @dp.message_handler(
        lambda message: message.text in ["08:00 (удалить)", "09:00 (удалить)", "10:00 (удалить)", "11:00 (удалить)",
                                         "12:00 (удалить)", "13:00 (удалить)", "14:00 (удалить)", "15:00 (удалить)",
                                         "16:00 (удалить)", "17:00 (удалить)", "18:00 (удалить)", "19:00 (удалить)"]
                        and Master.is_Master(message.from_user.id))
    async def process_delete_hours(message: types.Message):
        chat_id = message.chat.id
        selected_hour = message.text.split(' ')[0]  # Получаем выбранный час из текста сообщения

        # Проверяем, существует ли уже запись для данного мастера
        cursor.execute('SELECT * FROM WorkingHours WHERE Master=?', (chat_id,))
        existing_record = cursor.fetchone()

        if existing_record and existing_record[working_hours.index(selected_hour) + 2]:
            # Если запись существует и час отмечен как True, обновляем существующий час в соответствии с выбором мастера
            cursor.execute(f'''
                UPDATE WorkingHours
                SET "{selected_hour}" = ?
                WHERE Master = ?
            ''', (False, chat_id))

            # Сохраняем изменения в базе данных
            conn.commit()

            await bot.send_message(message.chat.id, f"Рабочие часы {selected_hour} успешно удалены!")
            await update_keyboard_delete(message)
        else:
            await bot.send_message(message.chat.id,
                                   f"Час {selected_hour} уже отмечен как удаленный или записи для вашего мастера нет в базе данных.")


    # Функция для обновления кнопок после изменений в базе данных для удаления
    async def update_keyboard_delete(message: types.Message):
        # Получаем текущий статус часов для конкретного мастера
        cursor.execute('SELECT * FROM WorkingHours WHERE Master = ?', (str(message.from_user.id),))
        result = cursor.fetchone()

        # Создаем кнопки только для тех часов, где статус равен True
        working_hours = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
                         "18:00", "19:00"]
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for hour in working_hours:
            if result and result[working_hours.index(hour) + 2]:  # Индекс 2 соответствует столбцам с часами в таблице
                keyboard.add(types.KeyboardButton(f"{hour} (удалить)"))

        back_btn = types.KeyboardButton('Назад')
        keyboard.add(back_btn)

        await bot.send_message(message.chat.id, "Выберите рабочие часы для удаления:", reply_markup=keyboard)

    back_btn = types.KeyboardButton('Назад')
    keyboard.add(back_btn)

    await bot.send_message(message.chat.id, "Выберите рабочие часы для удаления:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == 'Выбранные часы' and Master.is_Master(message.from_user.id))
async def my_hour_off(message: types.Message):
    # Получение списка рабочих часов из базы данных для конкретного мастера
    master_id = message.from_user.id
    cursor.execute('''SELECT "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00" FROM WorkingHours WHERE Master=?''', (str(master_id),))
    working_hours_records = cursor.fetchone()  # Предполагаем, что для мастера существует только одна запись

    if not working_hours_records:
        await message.answer("У вас нет выбранных рабочих часов.")
    else:
        # Форматирование и отправка списка рабочих часов с значением True
        selected_hours = [f"{hour}:00" for hour, is_selected in zip(range(8, 20), working_hours_records) if is_selected]
        formatted_working_hours_list = "\n".join(selected_hours)
        await message.answer(f"Ваши выбранные рабочие часы:\n{formatted_working_hours_list}")



#########################################################################################################



@dp.message_handler(lambda message: message.text == 'Мои выходные' and Master.is_Master(message.from_user.id))
async def masterdayoff(message: types.Message):
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        my_dayoff_btn = types.KeyboardButton('Выбранные выходные')
        add_dayoff_btn = types.KeyboardButton('Добавить выходной')
        delete_dayoff_btn = types.KeyboardButton('Удалить выходной')
        back_btn = types.KeyboardButton('Назад')
        keyboard.add(my_dayoff_btn, add_dayoff_btn, delete_dayoff_btn, back_btn)
        await bot.send_message(message.chat.id, "Выберите действие с выходными:", reply_markup=keyboard)


@dp.message_handler(lambda message: message.text == 'Добавить выходной' and Master.is_Master(message.from_user.id))
async def add_day_off(message: types.Message):
    chat_id = message.chat.id
    master_id = message.from_user.id  # Идентификатор мастера, делающего запрос

    # Получаем текущий год и месяц
    current_year, current_month, current_day = get_current_date()

    # Создаем клавиатуру с календарем на текущий месяц
    calendar_markup = create_calendar(current_year, current_month, current_day, master_id)

    # Проверяем выходные дни в базе данных и помечаем их как "Х"
    mark_existing_day_offs(calendar_markup, current_year, current_month, current_day, master_id)

    await bot.send_message(chat_id, "Выберите дату выходного дня:", reply_markup=calendar_markup)

def mark_existing_day_offs(markup, year, month, current_day, master_id):
    # Получаем выходные дни из базы данных для указанного года и месяца и для конкретного мастера
    cursor.execute('''SELECT Day FROM DayOff WHERE Year = ? AND Month = ? AND Master = ?''', (year, month, master_id))
    existing_day_offs = cursor.fetchall()


    # Преобразуем список кортежей в список целых чисел
    existing_day_offs = [day[0] for day in existing_day_offs]

    # Проходим по кнопкам календаря и помечаем выходные дни как "✔️", а предыдущие дни текущего месяца как "Х"
    for button in markup.inline_keyboard:
        for day_button in button:
            if day_button.text.isnumeric() and int(day_button.text) in existing_day_offs:
                day_button.text = "✔️"
                day_button.callback_data = "ignore"  # Меняем коллбэк для выходных дней


# Добавьте аргумент master_id в функцию create_calendar
def create_calendar(year, month, current_day, master_id):
    markup = InlineKeyboardMarkup(row_width=7)



    # Добавляем заголовки дней недели
    for weekday in calendar.day_name:
        markup.insert(InlineKeyboardButton(weekday[:2], callback_data="ignore"))

    # Получаем месяц в виде списка недель, каждая неделя - список дней
    month_calendar = calendar.monthcalendar(year, month)

    # Создаем кнопки для каждого дня месяца
    for week in month_calendar:
        for day in week:
            if day == 0:
                # Пустой день в календаре
                markup.insert(InlineKeyboardButton(" ", callback_data="ignore"))
            elif month == datetime.now().month:
                # Кнопка с номером дня текущего месяца
                if day > current_day:
                    markup.insert(InlineKeyboardButton(str(day), callback_data=f"day_off_{year}_{month}_{day}"))
                else:
                    markup.insert(InlineKeyboardButton("Х", callback_data=f"day_off_{year}_{month}_{day}"))
            elif month > datetime.now().month:
                # Кнопка с номером дня предыдущего месяца
                markup.insert(InlineKeyboardButton(str(day), callback_data=f"day_off_{year}_{month}_{day}"))
            else:
                # Кнопка с номером дня следующего месяца или дальнейшего будущего
                if year > datetime.now().year or (
                        year == datetime.now().year and month > datetime.now().month):
                    markup.insert(InlineKeyboardButton(str(day), callback_data=f"day_off_{year}_{month}_{day}"))
                else:
                    markup.insert(InlineKeyboardButton("Х", callback_data=f"day_off_{year}_{month}_{day}"))


    # Кнопка для перехода к предыдущему месяцу
    markup.insert(InlineKeyboardButton("<<", callback_data=f"prev_month_{year}_{month}"))
    # Добавляем заголовок с месяцем и годом
    markup.insert(InlineKeyboardButton(f"{calendar.month_name[month]} ", callback_data="ignore"))
    markup.insert(InlineKeyboardButton(f"{year}", callback_data="ignore"))
    # Кнопка для перехода к следующему месяцу
    markup.insert(InlineKeyboardButton(">>", callback_data=f"next_month_{year}_{month}"))

    return markup




@dp.callback_query_handler(lambda query: query.data.startswith(('prev_month', 'next_month')))
async def process_month_change(query: types.CallbackQuery):
    chat_id = query.message.chat.id
    master_id = query.from_user.id
    # Извлекаем год и месяц из коллбэк-данных
    _, _, year, month = query.data.split('_')
    year, month = int(year), int(month)

    # Вычисляем новый месяц в зависимости от нажатой кнопки
    if query.data.startswith('prev_month'):
        new_month = month - 1
        if new_month == 0:
            new_month = 12
            year -= 1
    else:
        new_month = month + 1
        if new_month == 13:
            new_month = 1
            year += 1


    # Получаем текущий день для нового месяца
    current_day = get_current_date()[2]

    # Создаем клавиатуру с календарем на новый месяц
    calendar_markup = create_calendar(year, new_month, current_day, master_id)

    # Проверяем выходные дни в базе данных и помечаем их
    mark_existing_day_offs(calendar_markup, year, new_month, current_day,master_id)

    # Опционально: можно отправить сообщение с подтверждением
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=query.message.message_id,
        text="Выберите дату выходного дня:",
        reply_markup=calendar_markup
    )


def get_current_date():
    current_date = datetime.now()
    return current_date.year, current_date.month, current_date.day

@dp.callback_query_handler(lambda query: query.data.startswith('day_off'))
async def process_day_off_callback(query: types.CallbackQuery):
    # Извлекаем год, месяц и день из данных коллбэка
    _, year, month, day = query.data.split('_')[1:]

    # Разбиваем day на две части, чтобы избежать ошибки
    day = int(day)

    # Записываем информацию о выходном дне в базу данных
    cursor.execute('''INSERT INTO DayOff (Master, Year, Month, Day)
                      VALUES (?, ?, ?, ?)''', (query.from_user.id, year, month, day))
    conn.commit()

    await bot.answer_callback_query(query.id, text=f"Добавлен выходной день: {day}.{month}.{year}")


    # Опционально: можно редактировать предыдущее сообщение с календарем
    await bot.edit_message_text(chat_id=query.message.chat.id,
                                message_id=query.message.message_id,
                                text=f"Добавлен выходной день: {day}.{month}.{year}")

################################################################Удаление выходного дня


@dp.message_handler(lambda message: message.text == 'Удалить выходной' and Master.is_Master(message.from_user.id))
async def dell_day_off(message: types.Message):
    # Здесь добавьте код для вывода списка инлайн-кнопок с датами выходных для выбранного мастера
    master_id = message.from_user.id
    print(master_id)
    day_off_buttons = get_day_off_buttons(master_id)
    # Создаем клавиатуру
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*day_off_buttons)
    await message.answer("Выберите дату выходного для удаления:", reply_markup=keyboard)


# Функция для получения инлайн-кнопок с датами выходных для выбранного мастера



def get_day_off_buttons(master_id):
    # Получаем текущую дату
    current_date = datetime.now()

    # Формируем запрос к базе данных, чтобы получить записи только после текущей даты + 3 дня
    cursor.execute(
        '''SELECT DISTINCT Year, Month, Day FROM DayOff WHERE Master = ? 
           AND (Year > ? OR (Year = ? AND Month > ?) OR (Year = ? AND Month = ? AND Day >= ?))
           ORDER BY Year ASC, Month ASC, Day ASC''',
        (master_id, current_date.year, current_date.year, current_date.month,
         current_date.year, current_date.month, current_date.day))

    day_off_records = cursor.fetchall()


    # Создаем список инлайн-кнопок
    buttons = []
    for record in day_off_records:
        year, month, day = record
        date_str = f"{day:02d}.{month:02d}.{year}"
        callback_data = f"delete_day_off_{year}_{month}_{day}"

        buttons.append(types.InlineKeyboardButton(date_str, callback_data=callback_data))

    return buttons


# Обработчик для удаления выходного по нажатию на инлайн-кнопку
@dp.callback_query_handler(lambda query: query.data.startswith('delete_day_off'))
async def delete_day_off_callback(query: CallbackQuery, state: FSMContext):
    # Извлекаем данные из callback_data
    data_parts = query.data.split('_')

    if len(data_parts) == 6:
        year, month, day = map(int, data_parts[3:])

        # Ваш код для удаления записи из таблицы DayOff
        cursor.execute('''DELETE FROM DayOff WHERE Master = ? AND Year = ? AND Month = ? AND Day = ?''',
                       (query.from_user.id, year, month, day))
        conn.commit()

        await bot.edit_message_text(chat_id=query.message.chat.id,
                                    message_id=query.message.message_id,
                                    text="Выходной успешно удален")
    else:
        await query.answer("Некорректный формат данных")


@dp.message_handler(lambda message: message.text == 'Выбранные выходные' and Master.is_Master(message.from_user.id))
async def my_day_off(message: types.Message):
    # Получение списка выходных из базы данных для конкретного мастера
    master_id = message.from_user.id
    cursor.execute('''SELECT Year, Month, Day FROM DayOff WHERE Master=?''', (str(master_id),))
    day_off_records = cursor.fetchall()

    if not day_off_records:
        await message.answer("У вас нет выбранных выходных.")
    else:
        # Форматирование и отправка списка выходных
        formatted_day_off_list = "\n".join([f"{record[0]}-{record[1]}-{record[2]}" for record in day_off_records])
        await message.answer(f"Ваши выбранные выходные:\n{formatted_day_off_list}")

########################################################Клиент#################################################################

@dp.message_handler(lambda message: message.text == 'Отменить запись')
async def cancel_record(message: types.Message, state: FSMContext):
    # Получаем chat_id клиента
    client_chat_id = str(message.from_user.id)

    # Получаем записи данного клиента из базы данных
    cursor.execute("SELECT ID, Master, Service, Year, Month, Week, Day, Time FROM Record WHERE Client = ? AND Pay = 1", (client_chat_id,))
    records = cursor.fetchall()


    # Если у клиента есть активные записи, создаем inline-кнопки
    if records:
        keyboard_markup = types.InlineKeyboardMarkup(row_width=1)

        for record in records:
            record_id, master, service, year, month, week, day, time = record
            callback_data = f"cancel_record:{record_id}"
            button_text = f"{str(day).zfill(2)}-{str(month).zfill(2)}-{year} {str(time).zfill(2)}:00"
            keyboard_markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))

        sent_message = await message.answer("Выберите запись для отмены:", reply_markup=keyboard_markup)
        await state.update_data(sent_message_id=sent_message.message_id)
    else:
        await message.answer("У вас нет активных записей для отмены.")

# ...

@dp.callback_query_handler(lambda query: query.data.startswith('cancel_record:'))
async def process_cancel_record(callback_query: types.CallbackQuery, state: FSMContext):
    # Извлекаем ID записи из callback_data
    record_id = int(callback_query.data.split(':')[1])

    # Получаем информацию о записи
    cursor.execute("SELECT Master, Service, Year, Month, Day, Time FROM Record WHERE ID = ?", (record_id,))
    record_info = cursor.fetchone()

    if record_info:
        master, service, year, month, day, time = record_info

        # Отправляем уведомление с вопросом о подтверждении отмены записи
        confirmation_text = f"Вы точно хотите отменить запись на {str(day).zfill(2)}-{str(month).zfill(2)}-{year} {str(time).zfill(2)}:00?"
        confirmation_keyboard = InlineKeyboardMarkup(row_width=2)
        confirmation_keyboard.add(
            InlineKeyboardButton("Да", callback_data=f"confirm_cancel:{record_id}"),
            InlineKeyboardButton("Нет", callback_data="cancel_cancel")
        )
        # Извлекаем ID ранее отправленного сообщения из состояния пользователя
        data = await state.get_data()
        sent_message_id = data.get("sent_message_id")

        # Редактируем ранее отправленное сообщение
        await bot.edit_message_text(confirmation_text, chat_id=callback_query.from_user.id, message_id=sent_message_id,
                                    reply_markup=confirmation_keyboard)


    else:
        # Если запись не найдена, отправляем уведомление
        await bot.send_message(callback_query.from_user.id, "Запись не найдена.")

# ...

@dp.callback_query_handler(lambda query: query.data.startswith('confirm_cancel:'))
async def confirm_cancel_record(callback_query: types.CallbackQuery, state: FSMContext):
    # Извлекаем ID записи из callback_data
    record_id = int(callback_query.data.split(':')[1])

    # Получаем информацию о записи
    cursor.execute("SELECT Master, Service, Year, Month, Day, Time FROM Record WHERE ID = ?", (record_id,))
    record_info = cursor.fetchone()

    if record_info:
        master, service, year, month, day, time= record_info

        # Отмечаем запись как отмененную в базе данных (или удаляем запись, в зависимости от вашего предпочтения)
        cursor.execute("DELETE FROM Record WHERE ID = ?", (record_id,))
        conn.commit()
        data = await state.get_data()
        sent_message_id = data.get("sent_message_id")
        # Отправляем уведомление об отмене записи
        cancel_message = f"К сожалению ваша запись на {str(day).zfill(2)}-{str(month).zfill(2)}-{year} {str(time).zfill(2)}:00 была отменена.😢 \nВозвращайтесь к нам снова.😊"
        await bot.edit_message_text(cancel_message, chat_id=callback_query.from_user.id, message_id=sent_message_id)

        master_notification = f"😢К сожалению запись на {str(day).zfill(2)}-{str(month).zfill(2)}-{year} {str(time).zfill(2)} была отменена.😢 Тайм-слот освобожден."
        await bot.send_message(master, master_notification)

        # Отвечаем на callback_query, чтобы закрыть всплывающее окно с кнопками
        await bot.answer_callback_query(callback_query.id, text="Запись отменена")

    else:
        # Если запись не найдена, отправляем уведомление
        await bot.send_message(callback_query.from_user.id, "Запись не найдена.")

# ...

@dp.callback_query_handler(lambda query: query.data == 'cancel_cancel')
async def cancel_cancel_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    # Отвечаем на callback_query, чтобы закрыть всплывающее окно с кнопками
    await bot.answer_callback_query(callback_query.id)
    data = await state.get_data()
    sent_message_id = data.get("sent_message_id")
    cancel_message = f"Спасибо, что не отменили запись.☺"
    # Отправляем сообщение с благодарностью за отмену отмены
    await bot.edit_message_text(cancel_message, chat_id=callback_query.from_user.id, message_id=sent_message_id)




@dp.message_handler(lambda message: message.text == 'Записаться')
async def book_appointment(message: types.Message):
    # Проверка наличия актуальной записи по чат айди и дате

    current_date = datetime.now().replace(microsecond=0)
    chat_id = str(message.chat.id)

    cursor.execute('''SELECT * FROM Record WHERE Chat_id=? AND Pay=?''',
                   (chat_id, True))
    existing_records = cursor.fetchall()

    for record in existing_records:
        # Преобразуем текстовые значения в целочисленные
        record_year = int(record[6])
        record_month = int(record[7])
        record_day = int(record[9])

        # Преобразуем время из строки в объект datetime
        record_time = datetime.strptime(record[10], "%H:%M").time()
        record_hour = int(record_time.strftime("%H"))
        record_minute = int(record_time.strftime("%M"))

        record_date = datetime(record_year, record_month, record_day, record_hour, record_minute)

        # Определяем просроченные записи
        if current_date < record_date:
            cursor.execute('''SELECT * FROM Master''')
            masters = cursor.fetchall()
            for master in masters:
                # Проверка наличия рабочих часов у мастера
                cursor.execute(
                    '''SELECT "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00" FROM WorkingHours WHERE Master=?''',
                    (master[2],))
            work_hours = cursor.fetchone()
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Записаться снова", callback_data="record_again"),
                InlineKeyboardButton("Отмена", callback_data="cancel_booking")
            )
            await message.answer("У вас уже имеется актуальная запись.😎", reply_markup=keyboard)
            return

    # Продолжаем код для выбора мастера, так как нет актуальных записей

    # Проверка наличия мастеров
    cursor.execute('''SELECT * FROM Master''')
    masters = cursor.fetchall()

    if not masters:
        await message.answer("☹Извините, в данный момент запись недоступна, так как нет доступных мастеров.☹")
        return

    # Вывод мастеров из таблицы в виде inline кнопок
    keyboard = InlineKeyboardMarkup()
    for master in masters:
        # Проверка наличия рабочих часов у мастера
        cursor.execute(
            '''SELECT "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00" FROM WorkingHours WHERE Master=?''',
            (master[2],))
        work_hours = cursor.fetchone()

        # Если у мастера есть рабочие часы, добавляем кнопку
        if work_hours and any(work_hours):
            keyboard.add(InlineKeyboardButton(master[1], callback_data=f"choose_master:{master[0]}"))

    # Проверка, есть ли доступные мастера
    if keyboard.inline_keyboard:
        await message.answer("Выберите мастера:", reply_markup=keyboard)
    else:
        await message.answer("☹Извините, в данный момент запись недоступна, так как нет мастеров с рабочими часами.☹")

@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('record_again'))
async def record_again(callback_query: types.CallbackQuery):
    cursor.execute('''SELECT * FROM Master''')
    masters = cursor.fetchall()
    # Вывод мастеров из таблицы в виде inline кнопок
    keyboard = InlineKeyboardMarkup()
    for master in masters:
        # Проверка наличия рабочих часов у мастера
        cursor.execute(
            '''SELECT "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00" FROM WorkingHours WHERE Master=?''',
            (master[2],))
        work_hours = cursor.fetchone()

        # Если у мастера есть рабочие часы, добавляем кнопку
        if work_hours and any(work_hours):
            keyboard.add(InlineKeyboardButton(master[1], callback_data=f"choose_master:{master[0]}"))

    if not masters:
        await bot.edit_message_text("☹Извините, в данный момент запись недоступна, так как нет доступных мастеров.☹",
                                    chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id)
        return

    # Вывод мастеров из таблицы в виде inline кнопок
    keyboard = InlineKeyboardMarkup()
    for master in masters:
        # Проверка наличия рабочих часов у мастера
        cursor.execute(
            '''SELECT "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00" FROM WorkingHours WHERE Master=?''',
            (master[2],))
        work_hours = cursor.fetchone()

        # Если у мастера есть рабочие часы, добавляем кнопку
        if work_hours and any(work_hours):
            keyboard.add(InlineKeyboardButton(master[1], callback_data=f"choose_master:{master[0]}"))

    # Проверка, есть ли доступные мастера
    if keyboard.inline_keyboard:
        await bot.edit_message_text("Выберите мастера:", chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id, reply_markup=keyboard)
    else:
        await bot.edit_message_text("Извините, в данный момент запись недоступна, так как нет мастеров с рабочими часами.",
                                    chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id)

@dp.callback_query_handler(lambda callback_query: callback_query.data == 'cancel_booking')
async def cancel_booking(callback_query: types.CallbackQuery):
    await bot.edit_message_text("Вы отказались от повторной записи.",
                                chat_id=callback_query.message.chat.id,
                                message_id=callback_query.message.message_id)




@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('choose_master:'))
async def choose_master(callback_query: types.CallbackQuery):
    # Получение данных о выбранном мастере из callback_data
    master_id = int(callback_query.data.split(":")[1])

    # Получение имени мастера из базы данных
    cursor.execute('''SELECT Name, Chat_id FROM Master WHERE ID=?''', (master_id,))
    master_data = cursor.fetchone()

    if master_data:
        master_name, master_chat_id = master_data

        # Получение услуг, которые предоставляет выбранный мастер
        cursor.execute('''SELECT s.ID, s.Name, s.Time  -- Добавляем поле Time
                          FROM MasterService ms
                          JOIN Service s ON ms.ServiceID = s.ID
                          WHERE ms.MasterID=?''', (master_id,))
        services = cursor.fetchall()

        if services:
            # Формируем сообщение с доступными услугами, включая время
            services_text = "\n".join([f"- {service[1]} ({service[2]})" for service in services])
            text = f"Выбранный вами мастер {master_name} выполняет следующие услуги с указанным временем:\n{services_text}"

            # Создаем клавиатуру с кнопками для каждой услуги
            keyboard = InlineKeyboardMarkup()
            for service in services:
                keyboard.add(InlineKeyboardButton(service[1], callback_data=f"choose_service:{master_id}:{service[0]}"))

            # Отправляем сообщение с текстом и клавиатурой
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text=text,
                                        reply_markup=keyboard)


def get_master_chat_id(master_id):
    cursor.execute('''SELECT Chat_id FROM Master WHERE ID=?''', (master_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None
def get_work_hours_from_database(master_id):
    master_chat_id = get_master_chat_id(master_id)
    # Получаем рабочие часы мастера из базы данных
    cursor.execute('SELECT * FROM WorkingHours WHERE Master = ?', (str(master_chat_id),))
    result = cursor.fetchone()
    # Получаем названия столбцов
    columns = [column[0] for column in cursor.description]

    # Создаем список для хранения рабочих часов
    work_hours = []

    # Выводим названия столбцов, где значение равно 1 (True)
    for i in range(2, len(columns)):  # Начинаем с индекса 2, так как 0 и 1 - это ID и Master
        if result[i] == 1:
            work_hours.append(columns[i])

    # Если нет информации о рабочих часах, возвращаем пустой список
    if not result:
        return []

    return work_hours

def get_busy_hours_from_database(master_id):
    # Получаем Chat_id мастера
    master_chat_id = get_master_chat_id(master_id)

    # Получаем занятые часы мастера из базы данных
    cursor.execute('''SELECT Year, Month, Day, Time 
                      FROM Record 
                      WHERE Master=?''',
                   (master_chat_id,))
    busy_hours = cursor.fetchall()
   
    # Преобразуем список кортежей в список целых чисел

    return busy_hours





@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('choose_service:'))
async def choose_service(callback_query: types.CallbackQuery):
        # Получение данных о выбранной услуге и мастере из callback_data
        data = callback_query.data.split(":")
        master_id = int(data[1])
        selected_service = data[2]
        chat_id = callback_query.message.chat.id

        # Получаем текущий год и месяц
        current_year, current_month, current_day = get_current_date()
        # Создаем клавиатуру с календарем на текущий месяц
        busy_hours = get_busy_hours_from_database(master_id)
        work_hours=get_work_hours_from_database(master_id)

        # Получение имени мастера и его chat_id из базы данных
        cursor.execute('''SELECT Name, Chat_id FROM Master WHERE ID=?''', (master_id,))
        master_data = cursor.fetchone()
        second_value = master_data[1]
        calendar_markup = create_clients_calendar(current_year, current_month, current_day, master_id, selected_service, busy_hours, work_hours)

        # Проверяем выходные дни в базе данных и помечаем их как "Х"
        mark_existing_day_offs(calendar_markup, current_year, current_month, current_day, second_value)
        await bot.edit_message_text("Выберите день записи: ", chat_id=callback_query.message.chat.id,
                                    message_id=callback_query.message.message_id, reply_markup=calendar_markup)


def is_busy_day(day, busy_hours, work_hours):
    # Получаем список занятых часов в выбранный день
    busy_hours_for_day = [hour[3] for hour in busy_hours if
                          (hour[0], hour[1], hour[2]) == (day.year, day.month, day.day)]


    # Преобразуем рабочие часы в виде списка строк с временами
    work_hours_strings = [str(hour) for hour in work_hours if hour is not None]


    # Проверяем, является ли день занятым
    return len(busy_hours_for_day) == len(work_hours_strings)


def create_clients_calendar(year, month, current_day, master_id, selected_service, busy_hours, work_hours):
    markup = InlineKeyboardMarkup(row_width=7)

    # Добавляем заголовки дней недели
    for weekday in calendar.day_name:
        markup.insert(InlineKeyboardButton(weekday[:2], callback_data="ignore"))

    # Получаем месяц в виде списка недель, каждая неделя - список дней
    month_calendar = calendar.monthcalendar(year, month)

    # Создаем кнопки для каждого дня месяца
    for week in month_calendar:
        for day in week:
            if day == 0:
                # Пустой день в календаре
                markup.insert(InlineKeyboardButton(" ", callback_data="ignore"))
            elif month == datetime.now().month:
                # Кнопка с номером дня текущего месяца
                current_date = datetime(year, month, day)
                if current_date > datetime.now():
                    if is_busy_day(current_date, busy_hours, work_hours):
                        markup.insert(InlineKeyboardButton("Ф", callback_data="ignore"))
                    else:
                        markup.insert(InlineKeyboardButton(str(day),
                                                           callback_data=f"day_record_{year}_{month}_{day}_{master_id}_{selected_service}"))
                else:
                    markup.insert(InlineKeyboardButton("Х", callback_data="ignore"))
            elif month > datetime.now().month:
                # Кнопка с номером дня предыдущего месяца
                current_date = datetime(year, month, day)
                if is_busy_day(current_date, busy_hours, work_hours):
                    markup.insert(InlineKeyboardButton("Ф", callback_data="ignore"))
                else:
                    markup.insert(InlineKeyboardButton(str(day),
                                                       callback_data=f"day_record_{year}_{month}_{day}_{master_id}_{selected_service}"))
            else:
                # Кнопка с номером дня следующего месяца или дальнейшего будущего
                current_date = datetime(year, month, day)
                if current_date > datetime.now():
                    if is_busy_day(current_date, busy_hours, work_hours):
                        markup.insert(InlineKeyboardButton("Ф", callback_data="ignore"))
                    else:
                        markup.insert(InlineKeyboardButton(str(day),
                                                           callback_data=f"day_record_{year}_{month}_{day}_{master_id}_{selected_service}"))
                else:
                    markup.insert(InlineKeyboardButton("Х", callback_data="ignore"))

    # Кнопка для перехода к предыдущему месяцу
    markup.insert(InlineKeyboardButton("<<", callback_data=f"prev_mon_{year}_{month}_{master_id}_{selected_service}"))
    # Добавляем заголовок с месяцем и годом
    markup.insert(InlineKeyboardButton(f"{calendar.month_name[month]} ", callback_data="ignore"))
    markup.insert(InlineKeyboardButton(f"{year}", callback_data="ignore"))
    # Кнопка для перехода к следующему месяцу
    markup.insert(InlineKeyboardButton(">>", callback_data=f"next_mon_{year}_{month}_{master_id}_{selected_service}"))

    return markup


@dp.callback_query_handler(lambda query: query.data.startswith(('prev_mon', 'next_mon')))
async def process_month_change(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id

    # Извлекаем год и месяц из коллбэк-данных
    _, _, year, month, master_id, selected_service  = callback_query.data.split('_')
    year, month = int(year), int(month)
    # Вычисляем новый месяц в зависимости от нажатой кнопки
    if callback_query.data.startswith('prev_mon'):
        new_month = month - 1
        if new_month == 0:
            new_month = 12
            year -= 1
    else:
        new_month = month + 1
        if new_month == 13:
            new_month = 1
            year += 1

    # Получаем текущий день для нового месяца
    current_day = get_current_date()[2]
    busy_hours = get_busy_hours_from_database(master_id)
    work_hours = get_work_hours_from_database(master_id)

    # Создаем клавиатуру с календарем на новый месяц
    calendar_markup = create_clients_calendar(year, new_month, current_day, master_id, selected_service,busy_hours,work_hours)

    # Проверяем выходные дни в базе данных и помечаем их
    mark_existing_day_offs(calendar_markup, year, new_month, current_day, master_id)

    # Опционально: можно отправить сообщение с подтверждением
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=callback_query.message.message_id,
        text="Выберите день для записи:",
        reply_markup=calendar_markup
    )


# Функция для проверки занятости часов


def is_hour_busy(master_id, year, month, day, hour):
    master_chat_id = get_master_chat_id(master_id)
    full_datetime = datetime(int(year), int(month), int(day), int(hour.split(":")[0]))

    # Преобразуем full_datetime в строку с временем
    formatted_time = full_datetime.strftime("%H:%M")

    cursor.execute('''SELECT COUNT(*) FROM Record
                      WHERE Master=? AND Year=? AND Month=? AND Day=? AND Time=?''',
                   (master_chat_id, year, month, day, formatted_time))
    result = cursor.fetchone()
    return result[0] > 0



# Callback-функция для обработки выбора времени
@dp.callback_query_handler(lambda query: query.data.startswith('day_record'))
async def process_day_off_callback(query: types.CallbackQuery, state: FSMContext):
    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)
    # Извлекаем год, месяц и день из данных коллбэка
    _, year, month, day, master_id, service = query.data.split('_')[1:]
    master_chat_id = get_master_chat_id(master_id)

    # Получение текущего статуса часов для конкретного мастера
    cursor.execute('SELECT * FROM WorkingHours WHERE Master = ?', (str(master_chat_id),))
    result = cursor.fetchone()

    # Создаем кнопки только для тех часов, где статус равен True
    working_hours = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00",
                     "19:00"]
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    for hour in working_hours:
        # Проверяем занятость часа
        is_busy = is_hour_busy(master_id, year, month, day, hour)

        if result and result[working_hours.index(hour) + 2] and not is_busy:
            keyboard.add(types.KeyboardButton(f"(Выбрать) {hour} "))

    back_btn = types.KeyboardButton('Назад')
    keyboard.add(back_btn)

    await bot.send_message(query.message.chat.id, "Выберите удобное для вас время:", reply_markup=keyboard)
    # Сохраняем данные о выборе даты в состоянии
    await state.update_data({'year': year, 'month': month, 'day': day, 'master_id': master_chat_id, 'service': service})
import asyncio

@dp.message_handler(lambda message: message.text in ["(Выбрать) 08:00", "(Выбрать) 09:00", "(Выбрать) 10:00", "(Выбрать) 11:00",
                                         "(Выбрать) 12:00", "(Выбрать) 13:00", "(Выбрать) 14:00", "(Выбрать) 15:00",
                                         "(Выбрать) 16:00", "(Выбрать) 17:00", "(Выбрать) 18:00", "(Выбрать) 19:00"])
async def process_recordhour_hours(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    selected_hour = message.text.split(' ')[1]  # Получаем выбранный час из текста сообщения
    data = await state.get_data()
    # Получаем необходимые параметры
    year = data['year']
    month = data['month']
    day = data['day']
    master_id = data['master_id']
    service = data['service']
    user_id = message.from_user.id



    cursor.execute('''SELECT RealName FROM Users WHERE Chat_id=?''', (str(user_id),))
    clientName = cursor.fetchone()

    # Получаем номер телефона клиента из таблицы Users
    cursor.execute('SELECT TelNumber FROM Users WHERE Chat_id = ?', (str(chat_id),))
    user_data = cursor.fetchone()
    cursor.execute('''SELECT Name FROM Service WHERE ID=?''', (str(service),))
    serviceName = cursor.fetchone()

    if user_data:
        tel_number = user_data[0]

        # Добавляем запись в таблицу Record
        cursor.execute('''
             INSERT INTO Record (Master, Service, Client, TelNumber, Chat_id, Year, Month, Day, Time, STATUS, Pay)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
         ''', (
        master_id, service, str(user_id), tel_number, str(chat_id), year, month, day, selected_hour, False, False))
        conn.commit()


    await state.update_data({'year': year, 'month': month, 'day': day, 'master_id': master_id, 'service': service, 'hour': selected_hour })
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    my_appointments_button = KeyboardButton("Мои актуальные записи")
    book_appointment_button = KeyboardButton("Записаться")
    cancel_entry = KeyboardButton("Отменить запись")

    # Добавляем кнопки на клавиатуру
    keyboard.add(my_appointments_button, book_appointment_button, cancel_entry)
    await bot.send_message(message.chat.id, "Необходимо внести предоплату:", reply_markup=keyboard)


    cursor.execute('SELECT Name, Time, Price FROM Service WHERE ID = ?', (str(service),))
    course_data = cursor.fetchone()

    if course_data:
        name = course_data[0]
        description = course_data[1]
        price = course_data[2]

        labeled_price = types.LabeledPrice(label="50% стоимости услуги", amount=int(price/2 * 100))
        # Отправляем инвойс для оплаты с превью-изображением
        invoice_message = await bot.send_invoice(message.chat.id,
                               title=name,
                               description=description,
                               provider_token=config.TOKEN_PAY,
                               currency="rub",
                               is_flexible=False,
                               prices=[labeled_price],
                               start_parameter="buy-service",
                               payload="invoice-payload",
                               photo_url="https://uploads.turbologo.com/uploads/design/preview_image/768686/preview_image20210713-19572-4hcmv9.png")

        # Получаем последний вставленный ID записи
        cursor.execute("SELECT last_insert_rowid()")
        last_inserted_id = cursor.fetchone()[0]

        # Используем ID записи как ключ для словаря invoice_messages
        invoice_messages[last_inserted_id] = invoice_message.message_id
        await asyncio.sleep(6000)
        asyncio.create_task(background_task2())


    else:
        await bot.send_message(message.chat.id, "Информация о услуге не найдена")

@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message, state: FSMContext):
    print("SUCCESSFUL_PAYMENT:")
    payment_info = message.successful_payment.to_python()
    for k, v in payment_info.items():
        print(f"{k} = {v}")

    user_id = message.from_user.id
    await set_payment_status(user_id, message.chat.id, state)

@dp.pre_checkout_query_handler(lambda query: True)
async def pre_checkout_query(pre_checkout_q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

def get_master_name(master_id):
    cursor.execute('''SELECT Name FROM Master WHERE Chat_id=?''', (master_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None

async def set_payment_status(user_id: int, chat_id: int, state: FSMContext):
    data = await state.get_data()
    year = data['year']
    month = data['month']
    day = data['day']
    master_id = data['master_id']
    service = data['service']
    selected_hour = data['hour']

    cursor.execute('''SELECT RealName FROM Users WHERE Chat_id=?''', (str(user_id),))
    clientName = cursor.fetchone()

    cursor.execute('SELECT TelNumber FROM Users WHERE Chat_id = ?', (str(chat_id),))
    user_data = cursor.fetchone()
    cursor.execute('''SELECT Name FROM Service WHERE ID=?''', (str(service),))
    serviceName = cursor.fetchone()

    if user_data:
        tel_number = user_data[0]

        # Обновляем статус оплаты в существующей записи
        cursor.execute('''
            UPDATE Record
            SET Pay=?
            WHERE Chat_id=? AND Year=? AND Month=? AND Day=? AND Time=?
        ''', (True, str(chat_id), year, month, day, selected_hour))
        conn.commit()

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        my_appointments_button = KeyboardButton("Мои актуальные записи")
        book_appointment_button = KeyboardButton("Записаться")
        cancel_entry = KeyboardButton("Отменить запись")

        keyboard.add(my_appointments_button, book_appointment_button, cancel_entry)

        await bot.send_message(chat_id, f"Ваша запись на {day}.{month}.{year} в {selected_hour} успешно оформлена!", reply_markup=keyboard)
        master_notification = f"❗У вас новая запись❗:\n" \
                              f"Услуга: {serviceName[0]}\n" \
                              f"Дата: {day}.{month}.{year}\n"\
                              f"Время: {selected_hour}\n" \
                              f"Клиент: {clientName[0]}\n"\
                              f"Телефон: {tel_number}"

        await bot.send_message(master_id, master_notification)




    else:
        await bot.send_message(chat_id, "Извините, не удалось найти ваши контактные данные. Пожалуйста, обновите профиль с вашими контактами.")

@dp.message_handler(lambda message: message.text == 'Мои актуальные записи')
async def my_appointments(message: types.Message, state: FSMContext):
    # Получаем чат ID пользователя
    chat_id = str(message.chat.id)

    # Выполняем запрос к базе данных для получения всех актуальных записей пользователя
    cursor.execute('''SELECT Record.*, Master.Name, Service.Name, Service.Price, Service.Time 
                      FROM Record 
                      INNER JOIN Master ON Record.Master = Master.Chat_id 
                      INNER JOIN Service ON Record.Service = Service.ID
                      WHERE Record.Chat_id=? AND Record.Pay=?''', (chat_id, True))
    records = cursor.fetchall()

    # Фильтруем записи, оставляя только актуальные
    current_date = datetime.now().replace(microsecond=0)
    current_appointments = []

    for record in records:
        # Преобразуем текстовые значения в целочисленные
        record_year = int(record[6])
        record_month = int(record[7])
        record_day = int(record[9])

        # Преобразуем время из строки в объект datetime
        record_time = datetime.strptime(record[10], "%H:%M").time()
        record_hour = int(record_time.strftime("%H"))
        record_minute = int(record_time.strftime("%M"))
        record_date = datetime(record_year, record_month, record_day, record_hour, record_minute)

        # Проверяем, актуальна ли запись
        if current_date < record_date:
            current_appointments.append(record)

    if current_appointments:
        # Если есть актуальные записи, формируем сообщение с информацией по актуальным записям
        appointments_message = "Ваши актуальные записи:\n\n"
        for record in current_appointments:
            appointment_info = f"Мастер: {record[13]}\nУслуга: {record[14]}\nДата: {record[9]}.{record[7]}.{record[6]}\nВремя: {record[10]}\nЦена: {record[15]}\nДлительность: {record[16]}\n\n"
            appointments_message += appointment_info

        # Отправляем сообщение с информацией о записях
        await message.answer(appointments_message)
    else:
        # Если у пользователя нет актуальных записей, отправляем сообщение об этом
        await message.answer("У вас пока нет актуальных записей.")



#################################################################Кнопка назад
@dp.message_handler(lambda message: message.text == 'Назад', state='*')
async def handle_back(message: types.Message, state: FSMContext):
    # Получаем предыдущее сообщение
    prev_message_id = message.message_id - 1

    try:
        # Пытаемся удалить предыдущее сообщение только из текущего диалога
        await bot.delete_message(message.chat.id, prev_message_id)
    except Exception as e:
        # Если не удается удалить, например, из-за ограничений бота, выводим ошибку
        print(f"Ошибка при удалении предыдущего сообщения: {e}")

    # Сбрасываем состояние
    await state.reset_state()

    # Выполняем нужные действия после команды "Назад"
    await process_start_command(message)

from datetime import datetime, timedelta

def get_service_name(service_id):
    cursor.execute('''SELECT Name, Time, Price FROM Service WHERE ID=?''', (service_id,))
    result = cursor.fetchone()
    if result:
        return result
    else:
        return None

async def background_task2():
    while True:
        # Фильтруем записи, оставляя только актуальные
        current_date = datetime.now().replace(microsecond=0)
        cursor.execute('''SELECT * FROM Record WHERE STATUS = ? AND Pay = ?''', (False, False))
        records = cursor.fetchall()

        for record in records:
            record_id, master, service, client, tel_number, chat_id, year, month, week, day, time, status, pay = record

            cancel_message = "Вы не оплатили запись в течение 10 минут. Запишитесь снова, если актуально."
            await bot.send_message(chat_id, cancel_message)
            master_notification = f"❗Неоплаченная запись удалена❗\n" \
                                  f"Мастер: {master}\n" \
                                  f"Дата: {day}.{month}.{year}\n" \
                                  f"Время: {time}\n" \
                                  f"Услуга: {service[0]}\n"

            await bot.send_message(chat_id, master_notification)

            invoice_message_id = invoice_messages.get(record_id)


            if invoice_message_id:
                # Удаляем сообщение с чатом (ID сообщения инвойса)
                await bot.delete_message(chat_id, invoice_message_id)

            # Удаляем запись
            cursor.execute("DELETE FROM Record WHERE ID = ?", (record_id,))
            conn.commit()




async def background_task():
    while True:
        # Фильтруем записи, оставляя только актуальные
        current_date = datetime.now().replace(microsecond=0)
        current_appointments = []
        cursor.execute('''SELECT * FROM Record WHERE (STATUS=? AND Pay=?)''', (False,True,))
        records = cursor.fetchall()

        for record in records:
            # Преобразуем текстовые значения в целочисленные
            record_year = int(record[6])
            record_month = int(record[7])
            record_day = int(record[9])
            # Преобразуем время из строки в объект datetime
            record_time = datetime.strptime(record[10], "%H:%M").time()
            record_hour = int(record_time.strftime("%H"))
            record_minute = int(record_time.strftime("%M"))
            record_date = datetime(record_year, record_month, record_day, record_hour, record_minute)
            # Разница во времени между записью и текущей датой
            time_difference = record_date - current_date

            # Проверяем, что разница в часах равна 24
            if time_difference < timedelta(hours=24):
                current_appointments.append(record)
                # Выводим информацию о записи
                chat_id, year, month, day, time, master, service = record[5], record[6], record[7], record[9], record[10], record[1], record[2]
                master_name = get_master_name(master)
                service_name = get_service_name(service)


                master_notification = f"❗У вас скоро запись❗\n" \
                                      f"Мастер: {master_name}\n" \
                                      f"Дата: {day}.{month}.{year}\n" \
                                      f"Время: {time}\n" \
                                      f"Услуга: {service_name[0]}\n" \
                                      f"Длительность: {service_name[1]}\n" \
                                      f"Стоимость: {service_name[2]}\n"

                await bot.send_message(chat_id, master_notification)
                # Обновляем STATUS на True после отправки уведомления
                cursor.execute('''UPDATE Record SET STATUS=? WHERE ID=?''', (True, record[0]))
                conn.commit()

        await asyncio.sleep(3600)

async def on_startup(dp):
    # Создаем фоновую задачу
    background_task_handle = asyncio.ensure_future(background_task())

    # Возвращаем фоновую задачу для возможности отмены
    return background_task_handle

async def on_shutdown(dp):
    # Отменяем фоновую задачу перед выходом
    await dp["background_task"].cancel()
    await dp["background_task2"].cancel()

cursor = conn.cursor()
if __name__ == "__main__":
    from aiogram import executor
    from Admin import (add_Master, add_Service, update_name_in_db, update_chat_id_in_db, update_nameservice_in_db,
                       update_time_in_db, update_price_in_db)
    # Запуск бота с обработчиками событий on_startup и on_shutdown
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)
    # Ожидание завершения бота
    executor.run(dp)





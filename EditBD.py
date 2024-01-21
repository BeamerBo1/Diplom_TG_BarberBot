import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('diplom.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS Record (
                         ID INTEGER PRIMARY KEY AUTOINCREMENT,
                         Master TEXT,
                         Service TEXT,
                         Client TEXT,
                         TelNumber TEXT,
                         Chat_id TEXT,
                         Year INT,
                         Month INT,
                         Week INT,
                         Day INT,
                         Time INT,
                         STATUS BOOLEAN,
                         Pay BOOLEAN
                     )''')

# Сохранение изменений
conn.commit()

# Закрытие соединения
conn.close()



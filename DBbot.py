import sqlite3


conn = sqlite3.connect('diplom.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS Admin (
                            ID INTEGER PRIMARY KEY AUTOINCREMENT,
                         Name TEXT,
                         Chat_id TEXT,
                         RealName TEXT
                        )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS Master (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Name TEXT,
                        Chat_id TEXT
                    )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS Users (
                         ID INTEGER PRIMARY KEY AUTOINCREMENT,
                         Name TEXT,
                         Chat_id TEXT,
                         TelNumber INTEGER,
                         RealName TEXT      
                     )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS Service (
                         ID INTEGER PRIMARY KEY AUTOINCREMENT,
                         Name TEXT,
                         Time Text,
                         Price INTEGER      
                     )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS WorkingHours (
                          ID INTEGER PRIMARY KEY AUTOINCREMENT,
                          Master TEXT,
                          "08:00" BOOLEAN,
                          "09:00" BOOLEAN,
                          "10:00" BOOLEAN,
                          "11:00" BOOLEAN,
                          "12:00" BOOLEAN,
                          "13:00" BOOLEAN,
                          "14:00" BOOLEAN,
                          "15:00" BOOLEAN,
                          "16:00" BOOLEAN,
                          "17:00" BOOLEAN,
                          "18:00" BOOLEAN,
                          "19:00" BOOLEAN
                      )''')

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

cursor.execute('''CREATE TABLE IF NOT EXISTS DayOff (
                  ID INTEGER PRIMARY KEY AUTOINCREMENT,
                  Master TEXT,
                  Year INTEGER,
                  Month INTEGER,
                  Day INTEGER
              )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS MasterService (
    ID INTEGER PRIMARY KEY,
    MasterID INTEGER,
    ServiceID INTEGER,
    FOREIGN KEY (MasterID) REFERENCES Master(ID),
    FOREIGN KEY (ServiceID) REFERENCES Service(ID),
    UNIQUE (MasterID, ServiceID)
            )''')



conn.commit()
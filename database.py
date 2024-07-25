import sqlite3


def create_tables():
    database = sqlite3.connect('database.db')
    cursor = database.cursor()

    # Create tokens table if it does not exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS tokens
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT UNIQUE, token TEXT)''')

    # Create couriers table if it does not exist
    cursor.execute('''CREATE TABLE IF NOT EXISTS couriers
                      (courier_id INTEGER PRIMARY KEY, lat REAL, long REAL)''')

    database.commit()
    database.close()

# save_token
def save_token(account, token):
    database = sqlite3.connect('database.db')
    cursor = database.cursor()
    cursor.execute("INSERT OR REPLACE INTO tokens (account, token) VALUES (?, ?)", (account, token))
    database.commit()
    database.close()


# get_token
def get_token(account):
    database = sqlite3.connect('database.db')
    cursor = database.cursor()
    cursor.execute("SELECT token FROM tokens WHERE account=?", (account,))
    token_row = cursor.fetchone()
    cursor.close()

    if token_row:
        return token_row[0]
    else:
        return " "


# save_or_update_courier
def save_or_update_courier(courier_id, lat, long):
    database = sqlite3.connect('database.db')
    cursor = database.cursor()

    # Check if the courier already exists
    cursor.execute("SELECT courier_id FROM couriers WHERE courier_id=?", (courier_id,))
    existing_courier = cursor.fetchone()

    if existing_courier:
        # Update the existing courier
        cursor.execute("UPDATE couriers SET lat=?, long=? WHERE courier_id=?", (lat, long, courier_id))
    else:
        # Insert a new courier
        cursor.execute("INSERT INTO couriers (courier_id, lat, long) VALUES (?, ?, ?)", (courier_id, lat, long))

    database.commit()
    database.close()



# get_courier
def get_courier(courier_id):
    database = sqlite3.connect('database.db')
    cursor = database.cursor()
    cursor.execute("SELECT courier_id, lat, long FROM couriers WHERE courier_id=?", (courier_id,))
    courier_row = cursor.fetchone()
    cursor.close()

    if courier_row:
        return {
            "courier_id": courier_row[0],
            "lat": courier_row[1],
            "long": courier_row[2]
        }
    else:
        return None

create_tables()
from pymongo.mongo_client import MongoClient
from urllib.parse import quote_plus

# Экранирование пароля
password = quote_plus("7F2aWCZTjhksWSIJ")  # Замените "your_password" на ваш реальный пароль

# Создание URI с экранированным паролем и параметром tls=true
uri = f"mongodb+srv://abushukurov0806:{password}@test.vtvgsul.mongodb.net/?retryWrites=true&w=majority"

# Создание нового клиента и подключение к серверу
client = MongoClient(uri)

# Выбор базы данных
db = client['database']

# Определение коллекций
tokens_collection = db['tokens']
couriers_collection = db['couriers']


# Сохранение токена
def save_token(account, token):
    tokens_collection.update_one(
        {'account': account},
        {'$set': {'token': token}},
        upsert=True
    )

# Получение токена
def get_token(account):
    token_document = tokens_collection.find_one({'account': account})
    if token_document:
        return token_document.get('token', '')
    return ' '

# Сохранение или обновление курьера
def save_or_update_courier(courier_id, lat, long):
    couriers_collection.update_one(
        {'courier_id': courier_id},
        {'$set': {'lat': lat, 'long': long}},
        upsert=True
    )

# Получение курьера
def get_courier(courier_id):
    courier_document = couriers_collection.find_one({'courier_id': courier_id})
    if courier_document:
        return {
            "courier_id": courier_document.get('courier_id'),
            "lat": courier_document.get('lat'),
            "long": courier_document.get('long')
        }
    return None


from flask import Flask, jsonify, request, render_template, redirect
from flask_socketio import SocketIO, emit
import requests
import json
from database import *
from flask_cors import CORS

import hashlib

from configs import *

app = Flask(__name__)
# socketio = SocketIO(app)
CORS(app)  # Разрешить CORS для всех маршрутов
socketio = SocketIO(app, cors_allowed_origins="*")


# OAuth2
@app.route('/auth', methods=['GET'])
def auth():
    code = request.args.get('code')
    account = request.args.get('account')

    url = f"https://{account}.joinposter.com/api/v2/auth/access_token"

    data = {
        'code': code,
        'application_id': application_id,
        'application_secret': application_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'

    }

    response = requests.post(url, data=data)

    if response.status_code == 200:
        json_data = response.json()
        access_token = json_data.get('access_token')
        save_token(account, access_token)

        return redirect(f"https://{account}.joinposter.com/manage/applications", code=302)


@app.route('/', methods=['POST'])
def handle_post():
    data_request = request.get_json()
    if 'data' in data_request:
        data_json = json.loads(data_request['data'])
        if 'transactions_history' in data_json and 'type_history' in data_json['transactions_history'] and \
                data_json['transactions_history']['type_history'] == 'changeprocessingstatus':
            # Выполняем GET-запрос
            transaction_id = data_request['object_id']
            token = get_token(data_request['account'])
            url = f"https://joinposter.com/api/dash.getTransaction?token={token}&transaction_id={transaction_id}&include_history=true&include_products=true&include_delivery=true"
            response = requests.get(url)
            # Выводим результат GET-запроса

            data = response.json()

            product_names_str = []  # Создаем пустой список для сохранения названий продуктов

            if 'response' in data and isinstance(data['response'], list):
                for item in data['response']:
                    processing_status = item.get('processing_status')
                    if int(processing_status) == 40:
                        if 'delivery' in item and 'courier_id' in item['delivery']:
                            courier_id = item['delivery']['courier_id']  # Сохраняем courier_id

                            # Если courier_id присутствует, отправляем запрос
                            response_employees = requests.get(
                                f'https://joinposter.com/api/access.getEmployees?token={token}')

                            # Проверяем успешность запроса
                            if response_employees.status_code == 200:
                                response_data = response_employees.json()
                                if 'response' in response_data:
                                    employees = response_data['response']
                                    for employee in employees:
                                        if isinstance(employee, dict) and 'user_id' in employee:
                                            if str(employee['user_id']) == str(courier_id):
                                                login = employee.get('login')
                                                username = login.split('@')[0]

                                                if 'products' in item:
                                                    for product in item['products']:
                                                        product_id = product['product_id']
                                                        product_num = int(float(product['num']))

                                                        # Формирование URL для запроса на получение информации о продукте
                                                        product_url = f"https://joinposter.com/api/menu.getProduct?token={token}&product_id={product_id}"

                                                        # Отправка запроса на получение информации о продукте
                                                        product_response = requests.get(product_url)

                                                        # Проверка успешности запроса
                                                        if product_response.status_code == 200:
                                                            product_data = product_response.json()
                                                            # Проверка наличия данных и наличия ключа 'product_name'
                                                            if 'response' in product_data and 'product_name' in \
                                                                    product_data['response']:
                                                                product_name = product_data['response']['product_name']

                                                                # Добавляем название продукта в общий список
                                                                product_names_str.append(
                                                                    f"{product_name} - {product_num}")

                                                        # print("Список всех продуктов:", product_names_str)

                                                product_text = '\n'.join(product_names_str)
                                                summa = data['response'][0].get('sum', '')

                                                # Если длина числа больше или равна 2, добавляем точку и форматируем как дробное число
                                                if len(summa) >= 2:
                                                    summa = f"{summa[:-2]}.{summa[-2:]}"
                                                # Если длина числа меньше 2, добавляем нуль в конце, чтобы иметь два знака после точки
                                                else:
                                                    summa = f"{summa}.{'0'.zfill(2)}"

                                                # найти процент скидку
                                                url_history = f"https://joinposter.com/api/dash.getTransactionHistory?token={token}&transaction_id={transaction_id}"
                                                order_history = requests.get(url_history)
                                                order_history = order_history.json()
                                                delivery_price = data['response'][0]['delivery'].get('delivery_price',
                                                                                                     0)

                                                discount_precent = 0
                                                for item in order_history['response']:
                                                    if item['type_history'] == 'changepromotioncount':
                                                        discount_precent = float(item['value'])

                                                summa = float(summa) - float(delivery_price)

                                                client_discount_precent = data['response'][0].get('discount', 0)

                                                if discount_precent > 0:
                                                    summa = (summa - (summa / 100) * float(discount_precent))
                                                    all_price = summa + delivery_price
                                                else:
                                                    summa = (summa - (summa / 100) * float(client_discount_precent))
                                                    all_price = summa + delivery_price

                                                client_money = data["response"][0]['delivery'].get("bill_amount", 0)
                                                change_money = client_money - all_price
                                                all_price = str(all_price) + '0'
                                                # ----------------------------------------------------------------------------->
                                                # Получаем номер телефона из данных и выводим его
                                                phone_number = data['response'][0].get('client_phone', '')

                                                # Если номер телефона не пустой, убираем пробелы из него
                                                if phone_number and phone_number != '':
                                                    phone_number = phone_number.replace(" ", "")

                                                # ----------------------------------------------------------------------------->
                                                delivery_time = data["response"][0]['delivery'].get('delivery_time', '')
                                                cleaned_delivery_time = delivery_time.rsplit(':', 1)[0]
                                                # ----------------------------------------------------------------------------->
                                                payments_url = f"https://joinposter.com/api/settings.getPaymentMethods?token={token}"
                                                payments_response = requests.get(payments_url).json()['response']
                                                desired_payment_id = data["response"][0]['delivery'].get(
                                                    'payment_method_id')
                                                payment_title = next(
                                                    (payment['title'] for payment in payments_response if payment.get(
                                                        'payment_method_id') == desired_payment_id),
                                                    "Не указан")
                                                # ----------------------------------------------------------------------------->
                                                message = f"""
=================
<b>Заказ</b> № {data["response"][0].get('transaction_id', '')}

<b>Заведение:</b>
{data_request.get('account', 'нет данных')}

<b>Доставить до:</b>
{cleaned_delivery_time}

<b>Клиент:</b>
{data["response"][0].get('client_firstname', '')} {data["response"][0].get('client_lastname', '')}

<b>Телефон:</b>
{phone_number}


<b>Адрес:</b>
{data['response'][0]['delivery'].get('address1', '')}
{data['response'][0]['delivery'].get('address2', '')}


<b>Координаты:</b>
{data["response"][0]['delivery'].get('lat', '')},{data["response"][0]['delivery'].get('lng', '')}


<b>Комментарий курьеру:</b>
{data['response'][0]['delivery'].get('comment', '')}


<b>Комментарий к чеку:</b>
{data["response"][0].get("transaction_comment", '')}


<b>Товары:</b>
{product_text}


<b>К оплате:</b> {all_price} 

<b>Метод оплаты:</b>  {payment_title}
<b>Купюры клиента:</b> {client_money}
<b>Сдача:</b> {change_money}
=================
                                                                                                                    """

                                                if username.isdigit():
                                                    data = {
                                                        "chat_id": int(username),
                                                        "message": message,
                                                        "transaction_id": data["response"][0].get('transaction_id', ''),
                                                        "summa": all_price,
                                                        "address": f"{data['response'][0]['delivery'].get('country', '')} {data['response'][0]['delivery'].get('city', '')} {data['response'][0]['delivery'].get('address1', '')}",
                                                        "account": data_request.get('account')
                                                    }

                                                    try:
                                                        socketio.emit('message', data)
                                                    except json.JSONDecodeError as e:
                                                        print("Error decoding JSON:", e)

                                                break
    if data_request['action'] == 'added' or data_request['action'] == 'closed':
        account = data_request.get('account', '')
        socketio.emit('data_update', account)
    return jsonify(message="POST request received"), 200


@app.route('/retry', methods=['POST'])
def handle_post_retry():
    data_request = request.get_json()
    if 'data' in data_request:
        data_json = json.loads(data_request['data'])
        if 'transactions_history' in data_json and 'type_history' in data_json['transactions_history'] and \
                data_json['transactions_history']['type_history'] == 'changeprocessingstatus':
            # Выполняем GET-запрос
            transaction_id = data_request['object_id']
            token = get_token(data_request['account'])
            url = f"https://joinposter.com/api/dash.getTransaction?token={token}&transaction_id={transaction_id}&include_history=true&include_products=true&include_delivery=true"
            response = requests.get(url)
            # Выводим результат GET-запроса

            data = response.json()

            product_names_str = []  # Создаем пустой список для сохранения названий продуктов

            if 'response' in data and isinstance(data['response'], list):
                for item in data['response']:
                    processing_status = item.get('processing_status')
                    if int(processing_status) == 40:
                        if 'delivery' in item and 'courier_id' in item['delivery']:
                            courier_id = item['delivery']['courier_id']  # Сохраняем courier_id

                            # Если courier_id присутствует, отправляем запрос
                            response_employees = requests.get(
                                f'https://joinposter.com/api/access.getEmployees?token={token}')

                            # Проверяем успешность запроса
                            if response_employees.status_code == 200:
                                response_data = response_employees.json()
                                if 'response' in response_data:
                                    employees = response_data['response']
                                    for employee in employees:
                                        if isinstance(employee, dict) and 'user_id' in employee:
                                            if str(employee['user_id']) == str(courier_id):
                                                login = employee.get('login')
                                                username = login.split('@')[0]

                                                if 'products' in item:
                                                    for product in item['products']:
                                                        product_id = product['product_id']
                                                        product_num = int(float(product['num']))

                                                        # Формирование URL для запроса на получение информации о продукте
                                                        product_url = f"https://joinposter.com/api/menu.getProduct?token={token}&product_id={product_id}"

                                                        # Отправка запроса на получение информации о продукте
                                                        product_response = requests.get(product_url)

                                                        # Проверка успешности запроса
                                                        if product_response.status_code == 200:
                                                            product_data = product_response.json()
                                                            # Проверка наличия данных и наличия ключа 'product_name'
                                                            if 'response' in product_data and 'product_name' in \
                                                                    product_data['response']:
                                                                product_name = product_data['response']['product_name']

                                                                # Добавляем название продукта в общий список
                                                                product_names_str.append(
                                                                    f"{product_name} - {product_num}")

                                                        # print("Список всех продуктов:", product_names_str)

                                                product_text = '\n'.join(product_names_str)
                                                summa = data['response'][0].get('sum', '')

                                                # Если длина числа больше или равна 2, добавляем точку и форматируем как дробное число
                                                if len(summa) >= 2:
                                                    summa = f"{summa[:-2]}.{summa[-2:]}"
                                                # Если длина числа меньше 2, добавляем нуль в конце, чтобы иметь два знака после точки
                                                else:
                                                    summa = f"{summa}.{'0'.zfill(2)}"

                                                # найти процент скидку
                                                url_history = f"https://joinposter.com/api/dash.getTransactionHistory?token={token}&transaction_id={transaction_id}"
                                                order_history = requests.get(url_history)
                                                order_history = order_history.json()
                                                delivery_price = data['response'][0]['delivery'].get('delivery_price',
                                                                                                     0)

                                                discount_precent = 0
                                                for item in order_history['response']:
                                                    if item['type_history'] == 'changepromotioncount':
                                                        discount_precent = float(item['value'])

                                                summa = float(summa) - float(delivery_price)

                                                client_discount_precent = data['response'][0].get('discount', 0)

                                                if discount_precent > 0:
                                                    summa = (summa - (summa / 100) * float(discount_precent))
                                                    all_price = summa + delivery_price
                                                else:
                                                    summa = (summa - (summa / 100) * float(client_discount_precent))
                                                    all_price = summa + delivery_price

                                                client_money = data["response"][0]['delivery'].get("bill_amount", 0)
                                                change_money = client_money - all_price
                                                all_price = str(all_price) + '0'
                                                # ----------------------------------------------------------------------------->
                                                # Получаем номер телефона из данных и выводим его
                                                phone_number = data['response'][0].get('client_phone', '')

                                                # Если номер телефона не пустой, убираем пробелы из него
                                                if phone_number and phone_number != '':
                                                    phone_number = phone_number.replace(" ", "")

                                                # ----------------------------------------------------------------------------->
                                                delivery_time = data["response"][0]['delivery'].get('delivery_time', '')
                                                cleaned_delivery_time = delivery_time.rsplit(':', 1)[0]
                                                # ----------------------------------------------------------------------------->

                                                payments_url = f"https://joinposter.com/api/settings.getPaymentMethods?token={token}"
                                                payments_response = requests.get(payments_url).json()['response']
                                                desired_payment_id = data["response"][0]['delivery'].get(
                                                    'payment_method_id')
                                                payment_title = next(
                                                    (payment['title'] for payment in payments_response if payment.get(
                                                        'payment_method_id') == desired_payment_id),
                                                    "Не указан")
                                                # ----------------------------------------------------------------------------->

                                                message = f"""
=================
<b>Повторный заказ</b> № {data["response"][0].get('transaction_id', '')}

<b>Заведение:</b>
{data_request.get('account', 'нет данных')}

<b>Доставить до:</b>
{cleaned_delivery_time}

<b>Клиент:</b>
{data["response"][0].get('client_firstname', '')} {data["response"][0].get('client_lastname', '')}

<b>Телефон:</b>
{phone_number}


<b>Адрес:</b>
{data['response'][0]['delivery'].get('address1', '')}
{data['response'][0]['delivery'].get('address2', '')}


<b>Координаты:</b>
{data["response"][0]['delivery'].get('lat', '')},{data["response"][0]['delivery'].get('lng', '')}


<b>Комментарий курьеру:</b>
{data['response'][0]['delivery'].get('comment', '')}


<b>Комментарий к чеку:</b>
{data["response"][0].get("transaction_comment", '')}


<b>Товары:</b>
{product_text}


<b>К оплате:</b> {all_price} 

<b>Метод оплаты:</b>  {payment_title}
<b>Купюры клиента:</b> {client_money}
<b>Сдача:</b> {change_money}
=================
                                                                                                                    """

                                                if username.isdigit():
                                                    data = {
                                                        "chat_id": int(username),
                                                        "message": message,
                                                        "transaction_id": data["response"][0].get('transaction_id', ''),
                                                        "summa": all_price,
                                                        "address": f"{data['response'][0]['delivery'].get('country', '')} {data['response'][0]['delivery'].get('city', '')} {data['response'][0]['delivery'].get('address1', '')}",
                                                        "account": data_request.get('account')
                                                    }

                                                    try:
                                                        socketio.emit('message', data)
                                                    except json.JSONDecodeError as e:
                                                        print("Error decoding JSON:", e)

                                                break
    return jsonify(message="successful"), 200


# connect
@socketio.on('connect')
def handle_connect():
    emit('connected', {'status': 'success', 'message': 'You are now connected to the server'})
    return jsonify(message="Connected !"), 200


# live_location
@socketio.on('live_location')
def live_location(data):
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    courier_id = data.get('courier_id')
    live_period = data.get('live_period')

    if latitude is not None and longitude is not None and courier_id is not None:
        # Отправка location с данными
        emit('location',
             {'latitude': latitude, 'longitude': longitude, 'courier_id': courier_id, 'live_period': live_period},
             broadcast=True)


# location
@socketio.on('location')
def location(data):
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    courier_id = data.get('courier_id')

    if latitude is not None and longitude is not None and courier_id is not None:
        save_or_update_courier(courier_id, latitude, longitude)
        # Отправка location с данными
        emit('location', {'latitude': latitude, 'longitude': longitude, 'courier_id': courier_id}, broadcast=True)


# get_location
@socketio.on('get_location')
def get_location(data):
    emit('get_location', data, broadcast=True)


# message
@socketio.on('message')
def handle_message(message):
    try:
        data = json.loads(message)
        emit('message', data, broadcast=True)
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)


# manage_platform
@app.route('/manage_platform/<code>')
def manage_platform(code):
    # получение токена
    auth = {
        'application_id': application_id,
        'application_secret': application_secret,
        'code': code
    }

    concatenated_string = ':'.join([auth['application_id'], auth['application_secret'], auth['code']])
    auth['verify'] = hashlib.md5(concatenated_string.encode()).hexdigest()

    response = requests.post('https://joinposter.com/api/v2/auth/manage', data=auth)

    if response.status_code == 200:
        # получение данных
        data = response.json()
        poster_token = data['access_token']

        # получение заказов
        url = f"https://joinposter.com/api/dash.getTransactions?token={poster_token}&include_delivery=true&status=1&service_mode=3"
        request_2 = requests.get(url)
        response_2 = request_2.json()
        response_2 = [item for item in response_2['response'] if item['processing_status'] == '40']

        # создание списка заказов
        orders = []
        for d in response_2:
            orders.append({
                'transaction_id': d['transaction_id'],
                'address1': d['delivery']['address1'],
                'address2': d['delivery']['address2'],
                'courier_id': d['delivery']['courier_id']
            })

        # запрос данных сотрудников
        response = requests.get(f'https://joinposter.com/api/access.getEmployees?token={poster_token}')
        employee_data = response.json().get('response', [])

        # сопоставление данных сотрудников с заказами
        for transaction in orders:
            for employee in employee_data:
                if transaction['courier_id'] == employee['user_id']:
                    transaction['courier_name'] = employee['name']
                    transaction['courier_login'] = employee['login']
                    break
            else:
                transaction['courier_id'] = ''
                transaction['courier_name'] = ''
                transaction['courier_login'] = ''

        # получение данных курьеров из базы данных
        if orders:
            database = sqlite3.connect('database.db')
            cursor = database.cursor()
            courier_logins = [order['courier_login'].split('@')[0] for order in orders if order['courier_login']]
            query = "SELECT courier_id, lat, long FROM couriers WHERE courier_id IN ({})".format(
                ','.join('?' * len(courier_logins))
            )
            cursor.execute(query, courier_logins)
            couriers = cursor.fetchall()
            cursor.close()

            # создание словаря координат курьеров
            courier_coords = {str(courier[0]): {'lat': courier[1], 'long': courier[2]} for courier in couriers}

            # добавление координат курьеров к заказам
            for order in orders:
                courier_login = order['courier_login'].split('@')[0]
                if courier_login in courier_coords:
                    order['courier_lat'] = courier_coords[courier_login]['lat']
                    order['courier_long'] = courier_coords[courier_login]['long']
                else:
                    order['courier_lat'] = ''
                    order['courier_long'] = ''

        # render_template
        return render_template("index.html", data=orders)


# manage_platform
@app.route('/manage_platform_pos/<company_name>', methods=['GET'])
def manage_platform_pos(company_name):
    token = get_token(company_name.lower())
    # --------------------------------------------------------------------->
    url = f"https://joinposter.com/api/dash.getTransactions?token={token}&include_delivery=true&status=1&service_mode=3"
    request_2 = requests.get(url)
    response_2 = request_2.json()
    response_2 = [item for item in response_2['response'] if item['processing_status'] == '40']

    # создание списка заказов
    orders = []
    for d in response_2:
        orders.append({
            'transaction_id': d['transaction_id'],
            'address1': d['delivery']['address1'],
            'address2': d['delivery']['address2'],
            'courier_id': d['delivery']['courier_id']
        })

    # запрос данных сотрудников
    response = requests.get(f'https://joinposter.com/api/access.getEmployees?token={token}')
    employee_data = response.json().get('response', [])

    # сопоставление данных сотрудников с заказами
    for transaction in orders:
        for employee in employee_data:
            if transaction['courier_id'] == employee['user_id']:
                transaction['courier_name'] = employee['name']
                transaction['courier_login'] = employee['login']
                break
        else:
            transaction['courier_id'] = ''
            transaction['courier_name'] = ''
            transaction['courier_login'] = ''

    # получение данных курьеров из базы данных
    if orders:
        database = sqlite3.connect('database.db')
        cursor = database.cursor()
        courier_logins = [order['courier_login'].split('@')[0] for order in orders if order['courier_login']]
        query = "SELECT courier_id, lat, long FROM couriers WHERE courier_id IN ({})".format(
            ','.join('?' * len(courier_logins))
        )
        cursor.execute(query, courier_logins)
        couriers = cursor.fetchall()
        cursor.close()

        # создание словаря координат курьеров
        courier_coords = {str(courier[0]): {'lat': courier[1], 'long': courier[2]} for courier in couriers}

        # добавление координат курьеров к заказам
        for order in orders:
            courier_login = order['courier_login'].split('@')[0]
            if courier_login in courier_coords:
                order['courier_lat'] = courier_coords[courier_login]['lat']
                order['courier_long'] = courier_coords[courier_login]['long']
            else:
                order['courier_lat'] = ''
                order['courier_long'] = ''

    # render_template

    return render_template("index.html", data=orders)


# order_close
@app.route('/order_close', methods=['POST'])
def order_close():
    if request.method == 'POST':
        data = request.json  # Получаем JSON-данные из POST-запроса

        if 'transaction_id' in data and 'account' in data:
            transaction_id = data['transaction_id']
            account = data['account']

            token = get_token(account)

            url = f"https://joinposter.com/api/dash.getTransaction?token={token}&transaction_id={transaction_id}&include_history=true&include_products=true&include_delivery=true"
            response = requests.get(url)
            data = response.json()

            if 'response' in data:
                spot_id = data["response"][0].get('spot_id', '')
                spot_tablet_id = data['response'][0]['history'][0][
                    'spot_tablet_id']

                # request for close order

                params = {
                    'token': token
                }

                transaction = {
                    'spot_id': int(spot_id),
                    'transaction_id': int(transaction_id),
                    'spot_tablet_id': int(spot_tablet_id),
                    "processing_status": 50
                }

                url = f'https://joinposter.com/api/transactions.updateTransaction?token={token}'

                response = requests.post(url, params=params, json=transaction)
                response = json.loads(response.text)

                if response.get("error") != 32:
                    return jsonify({"response": {"err_code": 0}}), 200
                else:
                    return jsonify({"response": {"err_code": 42}}), 200

    return jsonify({'error': 'Invalid request'}), 400


@socketio.on('update')
def update(data):
    company_name = data.get("company_name")
    token = get_token(company_name.lower())
    # --------------------------------------------------------------------->
    url = f"https://joinposter.com/api/dash.getTransactions?token={token}&include_delivery=true&status=1&service_mode=3"
    request_2 = requests.get(url)
    response_2 = request_2.json()
    response_2 = response_2["response"]

    # создание списка заказов
    orders = []
    for d in response_2:
        orders.append({
            'transaction_id': d['transaction_id'],
            'address1': d['delivery']['address1'],
            'address2': d['delivery']['address2'],
            'courier_id': d['delivery']['courier_id']
        })

    # запрос данных сотрудников
    response = requests.get(f'https://joinposter.com/api/access.getEmployees?token={token}')
    employee_data = response.json().get('response', [])

    # сопоставление данных сотрудников с заказами
    for transaction in orders:
        for employee in employee_data:
            if transaction['courier_id'] == employee['user_id']:
                transaction['courier_name'] = employee['name']
                transaction['courier_login'] = employee['login']
                break
        else:
            transaction['courier_id'] = ''
            transaction['courier_name'] = ''
            transaction['courier_login'] = ''

    # получение данных курьеров из базы данных
    if orders:
        database = sqlite3.connect('database.db')
        cursor = database.cursor()
        courier_logins = [order['courier_login'].split('@')[0] for order in orders if order['courier_login']]
        query = "SELECT courier_id, lat, long FROM couriers WHERE courier_id IN ({})".format(
            ','.join('?' * len(courier_logins))
        )
        cursor.execute(query, courier_logins)
        couriers = cursor.fetchall()
        cursor.close()

        # создание словаря координат курьеров
        courier_coords = {str(courier[0]): {'lat': courier[1], 'long': courier[2]} for courier in couriers}

        # добавление координат курьеров к заказам
        for order in orders:
            courier_login = order['courier_login'].split('@')[0]
            if courier_login in courier_coords:
                order['courier_lat'] = courier_coords[courier_login]['lat']
                order['courier_long'] = courier_coords[courier_login]['long']
            else:
                order['courier_lat'] = ''
                order['courier_long'] = ''

    emit('update_data', orders, broadcast=True)


if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

from itertools import cycle
from config import start_drivers_number_1, TOKEN, GROUP_ID
from database import insert_driver_data, is_driver_exists, delete_driver_by_number
from inference import CaptchaRecognizer
import requests
import base64
import time


def init_proxy_rotator(file_path='proxy_info.txt'):
    with open(file_path, 'r') as f:
        proxies_list = [line.strip() for line in f if line.strip()]
    return cycle(proxies_list)

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

user_agent_rotator = cycle(USER_AGENTS)


recognizer = CaptchaRecognizer()
proxy_rotator = init_proxy_rotator()

headers = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    'Connection': 'keep-alive',
    "Proxy-Connection": "keep-alive",
    "Host": "xn--b1afk4ade.xn--90adear.xn--p1ai",
    'Origin': 'https://xn--80aebkobnwfcnsfk1e0h.xn--p1ai',
    "Referer": "https://xn--80aebkobnwfcnsfk1e0h.xn--p1ai/",
    "Sec-Ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    "Sec-Ch-ua-mobile": "?0",
    "Sec-Ch-ua-platform": '"Linux"',
    "Sec-Fetch-dest": "empty",
    "Sec-Fetch-mode": "cors",
    "Sec-Fetch-site": "cross-site",
    "Sec-Fetch-storage-access": "active",
    "User-Agent": ""
}

def send_telegram_notification(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': GROUP_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    try:
        response = requests.post(url, json=payload,)
        return response.status_code == 200
    except Exception as e:
        print(f"Ошибка при отправке сообщения в Telegram: {e}")
        return False


proxies = {
    'http': None,
    'https': None
}

def rotate_proxy():
    global proxies
    next_proxy = next(proxy_rotator)
    proxies = {
        'http': next_proxy,
        'https': next_proxy
    }
    headers["User-Agent"] = next(user_agent_rotator)
    return proxies

def generate_driver_numbers():
    current = start_drivers_number_1
    while True:
        current += 1
        if current > 9999999999:
            current = 9900000001
        yield str(current)


def get_captcha(proxy=None):
    for _ in range(3):
        try:
            response = requests.get(
                url='https://xn--b1afk4ade.xn--90adear.xn--p1ai/captcha',
                headers=headers,
                timeout=30,
                proxies=proxy
            )
            return response.json()
        except Exception as e:
            print(f"Ошибка при получении капчи: {e}")
            time.sleep(5)
    return None


def recognize_captcha(base64_string):
    filename = "temp_captcha.jpg"
    try:
        with open(filename, "wb") as file:
            file.write(base64.b64decode(base64_string))
        return recognizer.recognize_captcha(filename, show_image=False)
    except Exception as e:
        print(f"Ошибка распознавания капчи: {e}")
        return None


def check_driver(driver_number):
    max_retries = 5  # Максимальное количество попыток
    retries = 0
    while retries < max_retries:
        current_proxy = rotate_proxy()
        time.sleep(5)
        try:
            captcha_data = get_captcha(current_proxy)
            if not captcha_data:
                print("Не удалось получить капчу")
                return False

            captcha_word = recognize_captcha(captcha_data["base64jpg"])
            if not captcha_word:
                print("Не удалось распознать капчу")
                retries += 1
                continue

            data = {
                'num': driver_number,
                'date': "",
                'captchaWord': captcha_word,
                'captchaToken': captcha_data["token"]
            }
            response = requests.post(
                url="https://xn--b1afk4ade.xn--90adear.xn--p1ai/proxy/check/driver",
                headers=headers,
                data=data,
                timeout=(10,30),
                proxies=current_proxy
            )
            response_json = response.json()

            if response_json.get('code') == 201:
                print(f"Неверная капча для номера {driver_number}, пробуем снова...")
                retries += 1
                time.sleep(1)
                continue

            if response_json['message'] == 'Ответ от серера получен. Записей о выдаче ВУ не найдено':
                print(f"Записей о выдаче ВУ не найдено {driver_number}")
                retries += 5
                time.sleep(1)
                continue
            if response_json['doc']["nameop"] == 'Замена ВУ в связи с истечением срока его действия' and \
                    response_json['doc']["codeop"] == '38':
                print(f"Было лишение права на ВУ {driver_number}")
                # Проверяем наличие записи в БД и удаляем если найдена
                if is_driver_exists({'num': driver_number}):
                    print(f"Найдена запись в БД для номера {driver_number}, удаляем...")
                    if delete_driver_by_number(driver_number):
                        print(f"Запись с номером {driver_number} успешно удалена из БД")
                        # Отправляем уведомление в Telegram об удалении
                        message = (
                            "🗑 <b>Запись удалена из базы!</b>\n\n"
                            f"📄 <b>Номер прав:</b> {driver_number}\n"
                            f"ℹ️ <b>Причина:</b> Лишение права управления ТС\n"
                            f"🔍 <b>Операция:</b> {response_json['doc']['nameop']}\n"
                            f"🔢 <b>Код операции:</b> {response_json['doc']['codeop']}"
                        )
                        if send_telegram_notification(message):
                            print("Уведомление об удалении отправлено в Telegram")
                        else:
                            print("Не удалось отправить уведомление об удалении в Telegram")
                    else:
                        print(f"Не удалось удалить запись с номером {driver_number} из БД")
                retries += 5
                time.sleep(1)
                continue

            if 'doc' in response_json and 'date' in response_json['doc']:
                year = int(response_json['doc']['date'][0:4])
                print(f"Номер: {driver_number}, год выдачи: {year}")
                if year >= 2023:
                    print(f"НАЙДЕН ПОДХОДЯЩИЙ НОМЕР: {driver_number}, год: {year}")
                    new_record = {
                        'num': response_json['doc']['num'],
                        'bdate': response_json['doc']['bdate'],
                        'date': response_json['doc']['date'],
                        'srok': response_json['doc']['srok'],
                        'cat': response_json['doc']['cat']
                    }
                    if not is_driver_exists(new_record):
                        record_id = insert_driver_data(new_record)
                        if record_id:
                            print(f"Данные успешно сохранены в базе с ID: {record_id}")

                            message = (
                                "🚀 <b>Найден новый номер!</b>\n\n"
                                f"📄 <b>Номер прав:</b> {new_record['num']}\n"
                                f"🎂 <b>Дата рождения:</b> {new_record['bdate']}\n"
                                f"📅 <b>Дата выдачи:</b> {new_record['date']}\n"
                                f"⏳ <b>Срок действия:</b> {new_record['srok']}\n"
                                f"📌 <b>Категории:</b> {new_record['cat']}\n\n"
                                f"🆔 <b>ID в базе:</b> {record_id}"
                            )
                            if send_telegram_notification(message):
                                print("Уведомление успешно отправлено в Telegram")
                            else:
                                print("Не удалось отправить уведомление в Telegram")

                        else:
                            print("Не удалось сохранить данные в базу")
                        return True
                    else:
                        print("Данные уже существуют в базе. Пропускаем.")
                        return False
                return False

        except Exception as e:
            print(f"Ошибка при проверке номера {driver_number}: {e}\n current_proxy: {current_proxy}")
            time.sleep(5)
            retries += 1

    return False


def main():
    number_generator = generate_driver_numbers()

    while True:
        try:
            driver_number = next(number_generator)
            print(f"Проверяем номер: {driver_number}")
            if check_driver(driver_number):
                pass
        except KeyboardInterrupt:
            print("Работа остановлена пользователем")
            break
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
import os
from datetime import datetime
from itertools import cycle
from PIL import Image, ImageDraw, ImageFont
import requests
import base64
import uuid
from inference import CaptchaRecognizer


def init_proxy_rotator(file_path='proxy_info.txt'):
    with open(file_path, 'r') as f:
        proxies_list = [line.strip() for line in f if line.strip()]
    return cycle(proxies_list)

os.makedirs('temp', exist_ok=True)
recognizer = CaptchaRecognizer()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_IMAGE = os.path.join(BASE_DIR, 'assets', 'input.JPG')
FONT_PATH = os.path.join(BASE_DIR, 'assets', 'arial.ttf')

USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

user_agent_rotator = cycle(USER_AGENTS)
proxy_rotator = init_proxy_rotator()

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
    return proxies

def get_current_headers():
    return {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Host": "xn--b1afk4ade.xn--90adear.xn--p1ai",
        "Origin": "https://xn--80aebkobnwfcnsfk1e0h.xn--p1ai",
        "Referer": "https://xn--80aebkobnwfcnsfk1e0h.xn--p1ai/",
        "Sec-Ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "Sec-Ch-ua-mobile": "?0",
        "Sec-Ch-ua-platform": '"Linux"',
        "Sec-Fetch-dest": "empty",
        "Sec-Fetch-mode": "cors",
        "Sec-Fetch-site": "cross-site",
        "User-Agent": next(user_agent_rotator)
    }


def get_captcha(headers, proxy):
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
        return None


def recognize_captcha(base64_string):
    try:
        with open("temp_captcha.jpg", "wb") as file:
            file.write(base64.b64decode(base64_string))
        return recognizer.recognize_captcha("temp_captcha.jpg", show_image=False)
    except Exception as e:
        print(f"Ошибка распознавания капчи: {e}")
        return None


def check_driver(driver_number, driver_date="", max_attempts=3):
    headers = get_current_headers()
    attempt = 0

    while attempt < max_attempts:
        current_proxy = rotate_proxy()
        attempt += 1
        print(f"Попытка {attempt} из {max_attempts}")

        captcha_data = get_captcha(headers=headers,proxy=current_proxy)
        if not captcha_data:
            return {"error": "Не удалось получить капчу"}

        captcha_word = recognize_captcha(captcha_data["base64jpg"])
        if not captcha_word:
            return {"error": "Не удалось распознать капчу"}

        data = {
            'num': driver_number,
            'date': driver_date,
            'captchaWord': captcha_word,
            'captchaToken': captcha_data["token"]
        }

        try:
            response = requests.post(
                url="https://xn--b1afk4ade.xn--90adear.xn--p1ai/proxy/check/driver",
                headers=headers,
                data=data,
                timeout=30,
                proxies=current_proxy
            )

            response_json = response.json()
            print("Ответ сервера:", response_json)

            if response_json.get('code') == 201:
                print("Неверная капча, пробуем снова...")
                continue  # Повторяем попытку

            if response_json.get('message') == 'Ответ от сервера получен. Записей о выдаче ВУ не найдено':
                return {"error": "Записей о выдаче ВУ не найдено"}

            if 'doc' not in response_json:
                error_msg = response_json.get('message', 'Неизвестная ошибка API')
                return {"error": f"Ошибка API: {error_msg}"}

            doc_data = response_json['doc']

            required_fields = ['num', 'bdate', 'date', 'srok', 'cat', 'status']
            if not all(field in doc_data for field in required_fields):
                return {"error": "Неполные данные в ответе API"}

            new_record = {
                'num': doc_data['num'],
                'bdate': doc_data['bdate'],
                'date': doc_data['date'],
                'srok': doc_data['srok'],
                'cat': doc_data['cat'],
                'status': 'Действует' if doc_data.get('status') == 'Т' else 'Не действует'
            }

            try:
                date = datetime.strptime(new_record['date'], '%Y-%m-%d')
                new_record['date'] = date.strftime('%d.%m.%Y')
                bdate = datetime.strptime(new_record['bdate'], '%Y-%m-%d')
                new_record['bdate'] = bdate.strftime('%d.%m.%Y')
                srok = datetime.strptime(new_record['srok'], '%Y-%m-%d')
                new_record['srok'] = srok.strftime('%d.%m.%Y')
            except Exception as e:
                print(f"Ошибка форматирования дат: {e}")
                return {"error": "Ошибка обработки дат"}

            try:
                if not os.path.exists(INPUT_IMAGE):
                    return {"error": "Не найден файл шаблона изображения"}

                image = Image.open(INPUT_IMAGE)
                draw = ImageDraw.Draw(image)

                texts = [
                    {"text": f"{new_record['num']} от {new_record['date']}", "position": (159, 50),
                     "color": (252, 161, 124), "font_size": 25},
                    {"text": f"{new_record['bdate']}", "position": (470, 233), "color": (70, 155, 204),
                     "font_size": 17},
                    {"text": f"{new_record['date']}", "position": (470, 259), "color": (70, 155, 204), "font_size": 17},
                    {"text": f"{new_record['srok']}", "position": (470, 285), "color": (70, 155, 204), "font_size": 17},
                    {"text": f"{new_record['cat']}", "position": (470, 311), "color": (70, 155, 204), "font_size": 17},
                    {"text": f"{new_record['status']}", "position": (470, 337), "color": (70, 155, 204),
                     "font_size": 17},
                ]

                for item in texts:
                    try:
                        font = ImageFont.truetype(FONT_PATH, size=item["font_size"])
                    except:
                        font = ImageFont.load_default()
                    draw.text(item["position"], item["text"], fill=item["color"], font=font)

                output_filename = f"result_{uuid.uuid4().hex}.png"
                output_path = os.path.join('temp', output_filename)
                image.save(output_path)

                new_record['image_path'] = output_path
                return new_record

            except Exception as e:
                print(f"Ошибка генерации изображения: {e}")
                return {"error": "Ошибка при генерации результата"}

        except requests.exceptions.RequestException as e:
            print(f"Ошибка POST-запроса: {e}")
            return {"error": "Ошибка соединения с API"}
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return {"error": "ВУ соответствующее запросу не существует"}

    return {"error": "Не удалось распознать капчу после нескольких попыток"}
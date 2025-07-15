import os

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import re
import requests
from datetime import datetime
from probiv import check_driver
from config import TOKEN, API_URL, GROUP_ID  # Добавляем GROUP_ID в импорт

bot = telebot.TeleBot(TOKEN)
user_data = {}

VALID_CATEGORIES = {'A', 'A1', 'B', 'B1', 'BE', 'C', 'C1', 'CE', 'C1E',
                    'D', 'D1', 'DE', 'D1E', 'M', 'Tm', 'Tb'}


@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id

    # Очищаем предыдущие данные
    if chat_id in user_data:
        user_data[chat_id] = {}

    # Отправляем приветственное сообщение
    welcome_msg = (
        "👋 Добро пожаловать!\n\n"
        "С помощью меня ты сможешь в пару кликов приобрести строку из базы ВУ для пробива на гибдд рф.\n"
        "🔐 Саппорт - @newqrx\n"
        "🚀 База обновлена по сегодняшний день"
    )

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💵Купить базу", callback_data="buy_db"))
    markup.add(InlineKeyboardButton("🔎Пробив по базе", callback_data="driver_license_check"))

    bot.send_message(chat_id, welcome_msg, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_db')
def buy_db(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    msg = bot.send_message(chat_id, "📅 Введите желаемую дату рождения:\n\n— Например: 01.02.1993")
    bot.register_next_step_handler(msg, process_bdate)


def process_bdate(message):
    chat_id = message.chat.id
    bdate_input = message.text

    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', bdate_input):
        msg = bot.send_message(chat_id,
                               "❌Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например: 01.02.1993")
        bot.register_next_step_handler(msg, process_bdate)
        return

    try:
        date_obj = datetime.strptime(bdate_input, '%d.%m.%Y')
        bdate = date_obj.strftime('%Y-%m-%d')
    except ValueError:
        msg = bot.send_message(chat_id,
                               "❌Такой даты не существует. Пожалуйста, введите корректную дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(msg, process_bdate)
        return

    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]['bdate'] = bdate

    markup = InlineKeyboardMarkup(row_width=4)
    row1 = [
        InlineKeyboardButton("A", callback_data="cat_A", parse_mode='HTML'),
        InlineKeyboardButton("B", callback_data="cat_B", parse_mode='HTML'),
        InlineKeyboardButton("C", callback_data="cat_C", parse_mode='HTML'),
        InlineKeyboardButton("D", callback_data="cat_D", parse_mode='HTML')
    ]
    row2 = [
        InlineKeyboardButton("BE", callback_data="cat_BE", parse_mode='HTML'),
        InlineKeyboardButton("CE", callback_data="cat_CE", parse_mode='HTML'),
        InlineKeyboardButton("DE", callback_data="cat_DE", parse_mode='HTML')
    ]
    row3 = [
        InlineKeyboardButton("🔎Поиск", callback_data="search")
    ]

    markup.add(*row1)
    markup.add(*row2)
    markup.add(*row3)

    bot.send_message(chat_id, "<b>🚔Выберите желаемую категорию прав:</b>", reply_markup=markup, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def handle_category_selection(call):
    chat_id = call.message.chat.id
    category = call.data.split('_')[1]

    if chat_id not in user_data:
        user_data[chat_id] = {}

    if 'categories' not in user_data[chat_id]:
        user_data[chat_id]['categories'] = set()

    # Переключаем состояние категории
    if category in user_data[chat_id]['categories']:
        user_data[chat_id]['categories'].remove(category)
    else:
        user_data[chat_id]['categories'].add(category)

    # Создаем новую клавиатуру
    markup = InlineKeyboardMarkup(row_width=4)
    row1 = [
        InlineKeyboardButton(
            text=f"A" + (" ✔️" if "A" in user_data[chat_id]['categories'] else ""),
            callback_data="cat_A",
            parse_mode='HTML'
        ),
        InlineKeyboardButton(
            text=f"B" + (" ✔️" if "B" in user_data[chat_id]['categories'] else ""),
            callback_data="cat_B",
            parse_mode='HTML'
        ),
        InlineKeyboardButton(
            text=f"C" + (" ✔️" if "C" in user_data[chat_id]['categories'] else ""),
            callback_data="cat_C",
            parse_mode='HTML'
        ),
        InlineKeyboardButton(
            text=f"D" + (" ✔️" if "D" in user_data[chat_id]['categories'] else ""),
            callback_data="cat_D",
            parse_mode='HTML'
        )
    ]
    row2 = [
        InlineKeyboardButton(
            text=f"BE" + (" ✔️" if "BE" in user_data[chat_id]['categories'] else ""),
            callback_data="cat_BE",
            parse_mode='HTML'
        ),
        InlineKeyboardButton(
            text=f"CE" + (" ✔️" if "CE" in user_data[chat_id]['categories'] else ""),
            callback_data="cat_CE",
            parse_mode='HTML'
        ),
        InlineKeyboardButton(
            text=f"DE" + (" ✔️" if "DE" in user_data[chat_id]['categories'] else ""),
            callback_data="cat_DE",
            parse_mode='HTML'
        )
    ]
    row3 = [
        InlineKeyboardButton("🔎Поиск", callback_data="search")
    ]

    markup.add(*row1)
    markup.add(*row2)
    markup.add(*row3)

    selected = ", ".join(sorted(user_data[chat_id]['categories'])) if user_data[chat_id]['categories'] else "не выбрано"

    try:
        bot.edit_message_text(
            text=f"<b>🚔Выберите желаемую категорию прав:</b>\nВыбранные категории: {selected}",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Ошибка при обновлении сообщения: {e}")


@bot.callback_query_handler(func=lambda call: call.data == 'search')
def handle_search(call):
    chat_id = call.message.chat.id

    if chat_id not in user_data or 'categories' not in user_data[chat_id] or not user_data[chat_id]['categories']:
        bot.answer_callback_query(call.id, "Пожалуйста, выберите хотя бы одну категорию!")
        return

    bot.answer_callback_query(call.id, "Ищем...")
    msg = bot.edit_message_text("Ищем данные...", chat_id, call.message.message_id)

    try:
        response = requests.get(API_URL, timeout=10)

        if response.status_code == 200:
            api_data = response.json().get('data', [])

            if not api_data:
                bot.edit_message_text("База данных пуста.", chat_id, msg.message_id)
                return

            user_data[chat_id]['api_data'] = api_data
            matching_bdate = [record for record in api_data if record.get('bdate') == user_data[chat_id]['bdate']]

            if not matching_bdate:
                bot.edit_message_text(
                    f"По дате рождения {user_data[chat_id]['bdate']} ничего не найдено.",
                    chat_id, msg.message_id
                )
                return

            matching_records = []
            available_categories = set()

            for record in matching_bdate:
                record_cats = set(record.get('cat', '').split(','))
                available_categories.update(record_cats)
                if user_data[chat_id]['categories'] & record_cats:
                    matching_records.append(record)

            if matching_records:
                user_data[chat_id]['found_records'] = matching_records
                date_groups = {}
                for record in matching_records:
                    try:
                        issue_date = datetime.strptime(record['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
                        if issue_date not in date_groups:
                            date_groups[issue_date] = set()
                        date_groups[issue_date].update(record['cat'].split(','))
                    except:
                        continue

                markup = InlineKeyboardMarkup()
                for issue_date, cats in sorted(date_groups.items(), reverse=True):
                    btn_text = f"{issue_date} | {', '.join(sorted(cats))}"
                    markup.add(InlineKeyboardButton(btn_text, callback_data=f"date_{issue_date}"))

                bot.edit_message_text(
                    "Выберите подходящие права:",
                    chat_id, msg.message_id,
                    reply_markup=markup
                )
            else:
                # Если категории не найдены
                not_found_msg = (
                    "На данный момент в нашей базе отсутствуют доступные ВУ по вашему запросу.\n\n"
                    "Доступные категории на эту дату:"
                )

                user_data[chat_id]['found_records'] = matching_bdate

                # Создаем словарь для группировки категорий по датам
                date_cat_groups = {}
                for record in matching_bdate:
                    try:
                        issue_date = datetime.strptime(record['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
                        cats = set(record.get('cat', '').split(','))

                        if issue_date not in date_cat_groups:
                            date_cat_groups[issue_date] = set()
                        date_cat_groups[issue_date].update(cats)
                    except:
                        continue

                # Создаем клавиатуру с кнопками
                markup = InlineKeyboardMarkup()
                for issue_date, cats in sorted(date_cat_groups.items(), reverse=True):
                    btn_text = f"{issue_date} | {', '.join(sorted(cats))}"
                    markup.add(InlineKeyboardButton(btn_text, callback_data=f"date_{issue_date}"))

                bot.edit_message_text(
                    not_found_msg,
                    chat_id,
                    msg.message_id,
                    reply_markup=markup
                )
        else:
            bot.edit_message_text(
                f"Ошибка API: {response.status_code}",
                chat_id, msg.message_id
            )

    except requests.exceptions.RequestException as e:
        bot.edit_message_text(
            f"Ошибка подключения к API: {str(e)}",
            chat_id, msg.message_id
        )
    except Exception as e:
        bot.edit_message_text(
            f"Неожиданная ошибка: {str(e)}",
            chat_id, msg.message_id
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith('date_'))
def handle_date_selection(call):
    chat_id = call.message.chat.id
    selected_date = call.data.split('_')[1]  # В формате ДД.ММ.ГГГГ

    if chat_id not in user_data or 'found_records' not in user_data[chat_id]:
        bot.send_message(chat_id, "Ошибка: данные не найдены. Пожалуйста, начните заново.")
        return
    try:
        date_compare = datetime.strptime(selected_date, '%d.%m.%Y').strftime('%Y-%m-%d')
    except:
        date_compare = selected_date

    records = []
    for r in user_data[chat_id]['found_records']:
        try:
            if r['date'] == date_compare or r['date'] == selected_date:
                records.append(r)
        except:
            continue

    if not records:
        bot.send_message(chat_id, f"По выбранной дате {selected_date} ничего не найдено.")
        return

    for record in records:
        try:
            srok_date = datetime.strptime(record['srok'], '%Y-%m-%d').strftime('%d.%m.%Y')
        except:
            srok_date = record['srok']

        try:
            issue_date = datetime.strptime(record['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        except:
            issue_date = record['date']

        message = (
            f"Номер прав: {record['num']}\n"
            f"Дата рождения: {record['bdate']}\n"
            f"Дата выдачи: {issue_date}\n"
            f"Срок действия: {srok_date}\n"
            f"Категории: {record['cat']}\n\n"
            "Лучшие строки - @qrx_draw_bot"
        )

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📋Купить ещё", callback_data="buy_more"))

        bot.send_message(chat_id, message, reply_markup=markup)

        try:
            user_info = bot.get_chat(chat_id)
            username = f"@{user_info.username}" if user_info.username else "без username"
            first_name = user_info.first_name or ""
            last_name = user_info.last_name or ""
            full_name = f"{first_name} {last_name}".strip()

            group_message = (
                f"Пользователь {username} {full_name}\n"
                f"купил строку ВУ:\n\n"
                f"Номер прав: {record['num']}\n"
                f"Дата рождения: {record['bdate']}\n"
                f"Дата выдачи: {issue_date}\n"
                f"Категории: {record['cat']}"
            )

            bot.send_message(GROUP_ID, group_message)
        except Exception as e:
            print(f"Ошибка при отправке уведомления в группу: {e}")

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_more')
def handle_buy_more(call):
    chat_id = call.message.chat.id
    if chat_id in user_data:
        user_data[chat_id] = {}
    bot.answer_callback_query(call.id)
    msg = bot.send_message(chat_id, "📅 Введите желаемую дату рождения:\n\n— Например: 01.02.1993")
    bot.register_next_step_handler(msg, process_bdate)


@bot.callback_query_handler(func=lambda call: call.data == 'driver_license_check')
def driver_license_check(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    msg = bot.send_message(chat_id, "🔢 Введите серийный номер водительского удостоверения:")
    bot.register_next_step_handler(msg, process_driver_number)


def process_driver_number(message):
    chat_id = message.chat.id
    driver_number = message.text.strip()

    if chat_id not in user_data:
        user_data[chat_id] = {}
    user_data[chat_id]['driver_number'] = driver_number

    msg = bot.send_message(chat_id, "📅 Введите дату выдачи в формате ДД.ММ.ГГГГ (например: 01.02.1993):")
    bot.register_next_step_handler(msg, process_driver_bdate)


def process_driver_bdate(message):
    chat_id = message.chat.id
    bdate_input = message.text

    if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', bdate_input):
        msg = bot.send_message(chat_id,
                               "❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например: 01.02.1993)")
        bot.register_next_step_handler(msg, process_driver_bdate)
        return

    try:
        date_obj = datetime.strptime(bdate_input, '%d.%m.%Y')
        bdate = date_obj.strftime('%Y-%m-%d')
    except ValueError:
        msg = bot.send_message(chat_id,
                               "❌ Такой даты не существует. Пожалуйста, введите корректную дату в формате ДД.ММ.ГГГГ")
        bot.register_next_step_handler(msg, process_driver_bdate)
        return

    if chat_id not in user_data or 'driver_number' not in user_data[chat_id]:
        bot.send_message(chat_id, "Ошибка: номер не найден. Пожалуйста, начните заново.")
        return

    driver_number = user_data[chat_id]['driver_number']

    processing_msg = bot.send_message(chat_id, "🔍 Проверяем данные... Это может занять некоторое время.")

    try:
        result = check_driver(driver_number, bdate)

        if result and 'image_path' in result:
            with open(result['image_path'], 'rb') as photo:
                bot.send_photo(chat_id, photo)

            try:
                os.remove(result['image_path'])
            except Exception as e:
                print(f"Ошибка при удалении временного файла: {e}")

        elif 'error' in result:
            bot.send_message(chat_id, f"❌ Ошибка: {result['error']}")
        else:
            bot.send_message(chat_id, "❌ Не удалось получить информацию по указанным данным.")

    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Произошла ошибка при проверке: {str(e)}")
    try:
        bot.delete_message(chat_id, processing_msg.message_id)
    except:
        pass
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
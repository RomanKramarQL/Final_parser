import psycopg2
from config import host, database, user, password, port


def insert_driver_data(driver_data):
    try:
        connection = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )

        with connection.cursor() as cursor:
            query = """
                INSERT INTO drivers (num, bdate, date, srok, cat)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """

            cursor.execute(query, (
                driver_data['num'],
                driver_data['bdate'],
                driver_data['date'],
                driver_data['srok'],
                driver_data['cat']
            ))
            inserted_id = cursor.fetchone()[0]
            connection.commit()

            print(f"Добавлены данные водителя с ID: {inserted_id}")
            return inserted_id

    except Exception as e:
        print(f"Ошибка при добавлении данных водителя: {e}")
        return None
    finally:
        if connection:
            connection.close()


def is_driver_exists(driver_data):
    try:
        connection = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1 FROM drivers 
                WHERE num = %s 
                AND bdate = %s 
                AND date = %s
                AND srok = %s
                AND cat = %s
                LIMIT 1;
            """, (driver_data['num'],
                  driver_data['bdate'],
                  driver_data['date'],
                  driver_data['srok'],
                  driver_data['cat']))

        return cursor.fetchone() is not None
    except Exception as e:
        print(f"Ошибка при проверке дубликата: {e}")
        return False
    finally:
        if connection:
            connection.close()

def check_db_connection():
    try:
        connection = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        print("✅ Подключение к PostgreSQL успешно!")
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к PostgreSQL: {e}")
        return False
    finally:
        if 'connection' in locals() and connection:
            connection.close()


def delete_driver_by_number(driver_number):
    try:
        connection = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM drivers WHERE num = ?", (driver_number,))
            connection.commit()

        return cursor.rowcount > 0
    except Exception as e:
        print(f"Ошибка при удалении записи из БД: {e}")
        return False
    finally:
        if connection:
            connection.close()


def get_drivers_by_number(driver_number, exact_match=True):
    """
    Поиск водителей по номеру (num)

    :param driver_number: Номер для поиска
    :param exact_match: True - точное совпадение, False - частичное совпадение
    :return: Список словарей с данными водителей или None при ошибке
    """
    try:
        connection = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )

        with connection.cursor() as cursor:
            if exact_match:
                query = """
                    SELECT id, num, bdate, date, srok, cat 
                    FROM drivers 
                    WHERE num = %s
                    ORDER BY date DESC
                """
                cursor.execute(query, (driver_number,))
            else:
                query = """
                    SELECT id, num, bdate, date, srok, cat 
                    FROM drivers 
                    WHERE num LIKE %s
                    ORDER BY date DESC
                """
                cursor.execute(query, (f"%{driver_number}%",))

            # Получаем все найденные записи
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results if results else None

    except Exception as e:
        print(f"Ошибка при поиске водителя по номеру: {e}")
        return None
    finally:
        if 'connection' in locals() and connection:
            connection.close()

a = get_drivers_by_number('9934002119')
print(a)
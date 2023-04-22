from psycopg2 import connect
## Удаление таблицы
def delete_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""Drop table if exists Users;""")
        conn.commit()
    return 'Таблицы успешно удалены'


## Функция, создающая структуру БД. Т.е. в данной функции создаются таблицы в базе данных
def create_table(conn):
    with conn.cursor() as cur:
        cur.execute("""create table if not exists Users (id serial primary key,
                    user_id integer not null,
                    pair_id integer not null,
                    CONSTRAINT user_pairs UNIQUE(user_id,pair_id)
                    );""")
        conn.commit()
    return 'Таблицы успешно созданы'

## Добавление пары для пользователя в БД
def add_user(conn, user_id, pair_id):
    with conn.cursor() as cur:
        cur.execute("""Insert into Users (user_id, pair_id)
                    values (%s,%s);""", (user_id, pair_id))
        conn.commit()
    return f'Пользователь {pair_id} успешно добавлен'

## Проверка на наличие пары в ДБ
def check_database(conn, user_id, pair_id):
    with conn.cursor() as cur:
        cur.execute("""Select pair_id from Users u
                    WHERE u.user_id =%s and u.pair_id =%s;""", (user_id, pair_id))
        check = cur.fetchone()
    return check

conn = connect(database="vkinder", user="postgres", password="waterpillar")

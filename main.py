import psycopg2, vk_api
from tokens import vktoken, group_token
from vk_api.longpoll import VkLongPoll, VkEventType

# ##Группы для поиска
# 10360575    87750784 201852825 199864025   202669543 207228548
# соционика1 соционика2   mbti    mbtimems1  mbtimems2   intp


vk_session = vk_api.VkApi(token=group_token)
user_session = vk_api.VkApi(token=vktoken)
session_api = vk_session.get_api()
longpool = VkLongPoll(vk_session)

def send_some_message(id, some_text):
      vk_session.method('messages.send', {'user_id': id, "message": some_text, "random_id": 0})


## Запрос о пользователе, общающимся с ботом
def get_user_info(id):
    info = vk_session.method('users.get',
                            {'user_id': id,
                            'fields': 'city, sex'})
    return info



## Запрос всех пользователей
def get_user_json(age, gender, city_id, group_id=None, offset=0):
    if group_id is None:
        database = user_session.method('users.search',
                                      {'city_id': city_id,
                                       'count': 1000,
                                       'sex': gender,
                                       'status': 6,
                                       'age_from': age,
                                       'age_to': age,
                                       'fields': 'has_photo',
                                       'offset': offset,
                                       'v': '5.131'
                                        }
                                       )
    else:
        database = user_session.method('users.search',
                                       {'city_id': city_id,
                                        'count': 1000,
                                        'sex': gender,
                                        'status': 6,
                                        'age_from': age,
                                        'age_to': age,
                                        'fields': 'has_photo',
                                        'group_id': group_id,
                                        'offset': offset,
                                        'v': '5.131'
                                        }
                                       )
    return database

def delete_tables(conn): ##Удаление таблицы
    with conn.cursor() as cur:
        cur.execute("""Drop table if exists Users;""")
    return "Таблицы успешно удалены"
    conn.commit()

def create_db(conn):  ##Функция, создающая структуру БД. Т.е. в данной функции создаются таблицы в базе данных
    with conn.cursor() as cur:
        cur.execute("""create table if not exists Users (id serial primary key,
                    user_id integer not null,
                    pair_id integer not null,
                    CONSTRAINT user_pairs UNIQUE(user_id,pair_id)
                    );""")
        conn.commit()
    return 'База данных успешно создана'

def get_users(conn):
    user_list = []
    try:
      for age in range (from_age, to_age + 1):
          data = get_user_json(age, gender, city_id, group_id, offset=0)
          count = data['count']
          for i in range(0, count, 1000):
            print(i)
            data = get_user_json(age, gender, city_id, group_id, offset=i)
            for user in data['items']:
                if user['is_closed'] is False: ## проверка на закрытый профиль
                    if user['has_photo'] == 1: ## проверка на наличие фото
                        pair_id = user['id']
                        first_name = user['first_name']
                        last_name = user['last_name']
                        with conn.cursor() as cur:
                            cur.execute("""Select pair_id from Users u
                                        WHERE u.user_id =%s and u.pair_id =%s;""", (id, pair_id))
                            check = cur.fetchone()
                        if check is None:
                            user_list.append([pair_id, last_name, first_name, age])
                        else:
                            continue
                    else:
                        continue
                else:
                    continue
    except:
        pass
    return user_list


def get_photo_json(id): ##Запрос фотографий
    photos = user_session.method('photos.get', {
                                'owner_id': id,
                                'album_id': 'profile',
                                'extended': 1,
                                'v': '5.131'
                                })
    return photos


with psycopg2.connect(database="vkinder", user="postgres", password="waterpillar") as conn:
    # delete_tables(conn)
    create_db(conn)
    get_users(conn)

## Держурство бота
for event in longpool.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        if event.to_me:
            msg = event.text.lower()
            id = event.user_id
            greetings = ["hi", "привет", "здравствуйте", "123", "хай", "hello", "как дела?"]
            if msg in greetings:
                send_some_message(id, f'Здравствуйте пользователь {id}, Вас приветствует ассистент Vkinder. '
                                      f'Чтобы начать поиск, введите "поиск".')
            elif msg == 'поиск':
                city_id = get_user_info(id)[0]["city"]["id"]
                send_some_message(id, f'Мы ищем пару из {get_user_info(id=id)[0]["city"]["title"]}, '
                                      f'введите желаемый возраст через диапазон, например "18, 55"')
                if get_user_info(id=id)[0]["sex"] == 1:
                    gender = 2
                elif get_user_info(id=id)[0]["sex"] == 2:
                    gender = 1
            elif len(msg.split(',')) == 2:
                try:
                    from_age = int(msg.split(',')[0])
                    to_age = int(msg.split(',')[-1])
                    group_id = None
                    send_some_message(id, 'Нужны дополнительные параметры (группы)? '
                                          'Если хотите, введите "группы". Иначе введите "начать поиск"')
                except:
                    print('попробуйте еще раз')
            elif msg == "группы":
                send_some_message(id, 'Введите id группы (9 цифр). Узнать id можно на https://regvk.com/id/')
            elif len(str(msg)) == 9:
                try:
                    if type(int(msg)) == int:
                        group_id = int(msg)
                        send_some_message(id, 'Пора начинать! Ведите "начать поиск"')
                except:
                    pass

            elif msg == "начать поиск":
                for user in get_users(conn):
                    send_some_message(id, f'{"https://vk.com/id" + str(user[0])} {user[1]}, {user[2]}, {user[3]}')
                    data = get_photo_json(id=user[0])
                    fotos = {}
                    if 'error' not in data:  ##error при достижении лимита запросов
                        items = data['items']
                        for item in items:
                            for photos in item['sizes']:  ##выбираем самые большие фотки и фильтруем по лайкам+комментариям
                                sizes = []
                                x = photos['width'] + photos['height']
                                y = item['likes']['count'] + item['comments']['count']
                                sizes.append([x, y, photos['url'].split('&c_uniq_tag')[0]])
                                max_size = max(sizes)
                            fotos.update({max_size[2]: max_size[1]})
                            s = sorted(fotos, key=fotos.get, reverse=True)[:3]
                    if len(s) == 1:
                        send_some_message(id, f'{s[0]}\n')
                    if len(s) == 2:
                        send_some_message(id, f'{s[0]}\n{s[1]}\n')
                    if len(s) == 3:
                        send_some_message(id, f'{s[0]}\n{s[1]}\n{s[2]}\n')
                    with conn.cursor() as cur:
                        cur.execute("""Insert into Users (user_id, pair_id)
                                    values (%s,%s);""", (id, user[0]))
                        conn.commit()
                send_some_message(id, "Поиск завершен. Удачи!")
conn.close()


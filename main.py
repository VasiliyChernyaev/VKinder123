from tokens import vktoken, group_token
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api import VkApi
from psycopg2 import connect
from database import delete_tables, create_table, add_user, check_database

vk_session = VkApi(token=group_token)
user_session = VkApi(token=vktoken)
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

## Список подходящих партнеров
def get_users(user_id):
    user_list = []
    for age in range(from_age, to_age + 1): ## Идем по возрасту, начиная с молодых
        data = get_user_json(age, gender, city_id, group_id, offset=0)
        count = data['count']
        for i in range(0, count + 1, 1000): ## Работа с оффсетом, если count > 1000
            data = get_user_json(age, gender, city_id, group_id, offset=i)
            for user in data['items']:
                if user['is_closed'] is False: ## проверка на закрытый профиль
                    if user['has_photo'] == 1: ## проверка на наличие фото
                        pair_id = user['id']
                        first_name = user['first_name']
                        last_name = user['last_name']
                        if check_database(conn, user_id=user_id, pair_id=pair_id) is None:
                            user_list.append([pair_id, last_name, first_name, age])
        if len(user_list) > profile_count:  ## Останавливаем цикл for age, если слишком много пользователей
            break
    return user_list

## Запрос фотографий
def get_photo_json(id):
    photos = user_session.method('photos.get', {
                                'owner_id': id,
                                'album_id': 'profile',
                                'extended': 1,
                                'v': '5.131'
                                })
    return photos

## Фотографии пользователей
def get_photos(id):
    fotos = {}
    data = get_photo_json(id=id)
    if 'error' not in data:  ##error при достижении лимита запросов
        items = data['items']
        for item in items:
            for photos in item['sizes']:  ##выбираем самые большие фотки и фильтруем по лайкам+комментариям
                sizes = []
                photo_size = photos['width'] + photos['height']
                photo_rating = item['likes']['count'] + item['comments']['count']
                sizes.append([photo_size, photo_rating, photos['url'].split('&c_uniq_tag')[0]])
                max_size = max(sizes)
            fotos.update({max_size[2]: max_size[1]})
            top3photos = sorted(fotos, key=fotos.get, reverse=True)[:3]
    return top3photos

## Переменные для дополнительных параметров поиска (по умолчанию)
first_message = 0
anketi = 0
groups = 0
profile_count = 100 ## Сколько анкет по умолчанию
## Держурство бота
for event in longpool.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        if event.to_me:
            msg = event.text.lower()
            id = event.user_id
            ## Первое сообщение боту
            if first_message == 0:
                send_some_message(id, f'Здравствуйте пользователь {id}, Вас приветствует ассистент Vkinder. '
                                      f'Чтобы начать поиск, введите "поиск".')
                first_message = 1
            ## Берем данные пользователя
            elif msg == 'поиск':
                city_id = get_user_info(id=id)[0]["city"]["id"]
                group_id = None
                send_some_message(id, f'Мы ищем пару из {get_user_info(id=id)[0]["city"]["title"]}, '
                                      f'введите желаемый возраст через диапазон, например "18, 55"')
                if get_user_info(id=id)[0]["sex"] == 1:
                    gender = 2
                elif get_user_info(id=id)[0]["sex"] == 2:
                    gender = 1
            ## Возрастной диапазон, через запятую from_age, to_age
            elif len(msg.split(',')) == 2:
                try:
                    from_age = int(msg.split(',')[0])
                    to_age = int(msg.split(',')[-1])
                    send_some_message(id, 'Нужны дополнительные параметры (группы, кол-во анкет)? '
                                          'Если хотите, введите "группы" или "анкеты". Иначе введите "начать поиск"')
                except:
                    send_some_message(id, 'Ошибка диапазона, если вам нужен определенный возраст'
                                                 'используйте его через запятую, например "25,25"')
            ## Дополнительная сортировка по одной группе
            elif msg == "группы":
                send_some_message(id, 'Введите id группы (9 цифр). Узнать id можно на https://regvk.com/id/')
                groups = 1
            elif groups == 1:
                try:
                    if len(str(msg)) == 9 and type(int(msg)) == int:
                        group_id = int(msg)
                        send_some_message(id, 'Сортировка по группе добавлена! Ведите "начать поиск"')
                        groups = 0
                except:
                    send_some_message(id, "ID группы состоит только из цифр")
            ## Даем пользователю ввести сколько ему нужно анкет
            elif msg == "анкеты":
                send_some_message(id, 'Введите нужное количество анкет, максимум 1000 (по умолчанию 100)')
                anketi = 1
            elif anketi == 1:
                try:
                    if int(msg) in range(1, 1001):
                        profile_count = int(msg)
                        send_some_message(id, f'Количество отображаемых анкет — {profile_count}. Можно начинать поиск.')
                        anketi = 0
                    else:
                        send_some_message(id, 'Используйте диапазон от 1 до 1000.')
                except:
                    send_some_message(id, "Введите число без каких-либо других символов")
            ## Начинаем поиск, подключаемся к БД
            elif msg == "начать поиск":
                with connect(database="vkinder", user="postgres", password="postgres") as conn:
                    # delete_tables(conn) ## Удалить таблицу, если необходимо
                    create_table(conn) ## Создаем таблицу user + пара, когда пользователь запустил поиск
                    try:
                        for user in get_users(user_id=id)[:profile_count]: ## кол-во профилей за сессию
                            send_some_message(id, f'{"https://vk.com/id" + str(user[0])} {user[1]}, {user[2]}, {user[3]}')
                            send_some_message(id, '\n'.join(str(link) for link in get_photos(id=user[0])))
                            add_user(conn, user_id=id, pair_id=user[0]) ##Добавили пару в БД
                    except:
                        send_some_message(id, "Ошибка запроса, попробуте позже")
                    send_some_message(id, "Поиск завершен. Удачи!")
                conn.close()

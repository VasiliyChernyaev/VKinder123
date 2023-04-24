from tokens import vktoken, group_token
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api import VkApi, VkUpload
from vk_api.utils import get_random_id
from database import delete_tables, create_table, add_user, check_database, conn

vk_session = VkApi(token=group_token)
user_session = VkApi(token=vktoken)
session_api = vk_session.get_api()
longpool = VkLongPoll(vk_session)
upload = VkUpload(vk_session)

def send_some_message(id, some_text):
    vk_session.method('messages.send', {'user_id': id, "message": some_text, "random_id": get_random_id()})

def send_photo(id):
    vk_session.method('messages.send', {'user_id': id, "random_id": get_random_id(), 'attachment': ','.join(attachments)})

## Запрос о пользователе, общающимся с ботом
def get_user_info(id):
    info = vk_session.method('users.get',
                             {'user_id': id,
                              'fields': 'city, sex'})
    return info


## Запрос всех пользователей
def get_user_json(age, gender, city_id, group_id=None, offset=0):
    params = {'city_id': city_id,
                'count': 1000,
                'sex': gender,
                'status': 6,
                'age_from': age,
                'age_to': age,
                'fields': 'has_photo',
                'offset': offset,
                'v': '5.131',
                'group_id': group_id
                }

    if group_id is None:
        params.popitem()
## Добавляем fields в json запрос, если дополнительные поля включены
    if options['advanced'] is True:
        for field in advanced_fields.keys():
            if options[field] is True:
                params.update({"fields": f'{params.get("fields")}, {field}'})

    database = user_session.method('users.search', params)
    return database


## Список подходящих партнеров
def get_users(user_id):
    user_list = []
    ## Идем по возрасту, начиная с молодых
    for age in range(from_age, to_age + 1):
        data = get_user_json(age, gender, city_id, group_id, offset=0)
        count = data['count']
        ## Работа с оффсетом, если count > 1000
        for i in range(0, count + 1, 1000):
            data = get_user_json(age, gender, city_id, group_id, offset=i)
            for user in data['items']:
                if user['is_closed'] is False:  ## проверка на закрытый профиль
                    if user['has_photo'] == 1:  ## проверка на наличие фото
                        pair_id = user['id']
                        first_name = user['first_name']
                        last_name = user['last_name']
                        person = [pair_id, last_name, first_name, age]
                        if check_database(conn, user_id=user_id, pair_id=pair_id) is None:
                            if options['advanced'] is False:  ## Поиск без доп.параметров
                                user_list.append(person)
                            else:
                                for field in advanced_fields.keys():
                                    if field in user:  ## Есть ли доп.параметр в данных пользователя
                                        if len(user[field]) > 0:
                                            person.append({field: user[field]})
                                if options['only_advanced'] is True:
                                    if len(person) > 4:  ## если fields пустые, будет ровно 4 элемента в листе
                                        user_list.append(person)
                                else:
                                    user_list.append(person)
        print(id, len(user_list), 'всего после фильтрации')  ## Длина листа. Полезна при поиске по интересам
        if len(user_list) > profile_count: ## Останавливаем цикл for age, если слишком много пользователей
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
                photo_id = item['id']
                sizes.append([photo_size, photo_rating, photo_id])
                max_size = max(sizes)
            fotos.update({max_size[2]: max_size[1]})
            top3photos = sorted(fotos, key=fotos.get, reverse=True)[:3]
    return top3photos


## Перевод vk.fields на русский язык + заглавная буква
def replace_dict_keys(user: list):
    words = {'interests': "Интересы", 'music': "Музыка", 'books': "Книги", 'games': "Игры",
             'about': "О себе", 'movies': "Фильмы", 'tv': "Сериалы", 'quotes': "Цитаты"}
    for dict in user[4:]:
        for key, value in words.items():
            if key in dict.keys():
                dict[value] = dict.pop(key)
    return user


## Переменные для дополнительных параметров поиска (по умолчанию)
from_age = 18
to_age = 35
group_id = None
profile_count = 5
options = {'first_message': False, 'age': False, 'forms': False, 'groups': False, 'advanced': False,
           'only_advanced': False, 'interests': False, 'games': False, 'music': False, 'books': False,
           'tv': False, 'movies': False, 'about': False, 'quotes': False}

## Держурство бота
for event in longpool.listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        msg = event.text.lower()
        id = event.user_id
        ## Первое сообщение боту, берем данные пользователя
        if options['first_message'] is False:
            user_name = get_user_info(id=id)[0]["first_name"]
            city_id = get_user_info(id=id)[0]["city"]["id"]
            if get_user_info(id=id)[0]["sex"] == 1:
                gender = 2
            elif get_user_info(id=id)[0]["sex"] == 2:
                gender = 1
            send_some_message(id, f'Здравствуйте {user_name}, Вас приветствует ассистент Vkinder.\n'
                                    f'Мы ищем пару из {get_user_info(id=id)[0]["city"]["title"]}. Возраст: 18-35 лет.\n \n'
                                    'Нужно настроить параметры (возрастной диапазон, группы, дополнительные поля, кол-во анкет)? '
                                    'Тогда введите "возраст", "группы", "дополнительно" или "анкеты". \n \n'
                                    'Чтобы начать поиск, введите "поиск"')
            options['first_message'] = True
        ## Возрастной диапазон, через запятую from_age, to_age
        elif msg == 'возраст':
            send_some_message(id, 'Введите желаемый возрастной диапазон через дефис, например "18-55". '
                                      'Поиск ведется от младшего к старшему.')
            options['age'] = True
        elif options['age'] is True:
            if len(msg.split('-')) == 2:
                try:
                    from_age = int(msg.split('-')[0])
                    to_age = int(msg.split('-')[-1])
                    send_some_message(id, f'Возрастной диапазон в годах установлен с {from_age} по {to_age}')
                    options['age'] = False
                except:
                    send_some_message(id, 'Ошибка диапазона, используйте только цифры. Если вам нужен один возраст,'
                                              'также введите его через дефис, например "25-25"')
            else:
                send_some_message(id, 'Используйте дефис "-", например "20-30"')
        ## Дополнительная сортировка по одной группе
        elif msg == "группы":
            send_some_message(id, 'Введите id группы (9 цифр). Узнать id можно на https://regvk.com/id/')
            options['groups'] = True
        elif options['groups'] is True:
            try:
                if type(int(msg)) == int:
                    group_id = int(msg)
                    send_some_message(id, 'Сортировка по группе добавлена! Можно начинать "поиск"')
                    options['groups'] = False
            except:
                send_some_message(id, "ID группы состоит только из цифр")
        ## Даем пользователю ввести сколько ему нужно анкет
        elif msg == "анкеты":
            send_some_message(id, 'Введите нужное количество анкет, максимум 50 (по умолчанию 5)')
            options['forms'] = True
        elif options['forms'] is True:
            try:
                if int(msg) in range(1, 51):
                    profile_count = int(msg)
                    send_some_message(id, f'Количество отображаемых анкет — {profile_count}. Можно начинать "поиск"')
                    options['forms'] = False
                else:
                    send_some_message(id, 'Используйте диапазон от 1 до 50')
            except:
                send_some_message(id, "Введите число без каких-либо других символов.")
        ## Дополнительные поля (интересы)
        elif msg == "дополнительно":
            options['advanced'] = True
            ## Дополнительные параметры
            advanced_fields = {'interests': 'интересы', 'music': 'музыка', 'books': 'книги', 'games': 'игры',
                                    'tv': 'сериалы', 'movies': 'фильмы', 'about': 'о себе', 'quotes': 'цитаты'}
            send_some_message(id, 'Для отображения доп.поля, введите его название. \n'
                                    'Доступные поля: интересы, игры, музыка, книги, сериалы, фильмы, о себе, цитаты.'
                                    'Чтобы активировать все поля, введите "все". \n'
                                    'Чтобы поиск производился ТОЛЬКО если у пары есть доп.поле, введите "только". ')
        ## Включаем fields в json запрос
        elif options['advanced'] is True and msg in advanced_fields.values():
            for key, value in advanced_fields.items():
                if advanced_fields[key] == msg:
                    options[key] = True
                    send_some_message(id, f'Поле {msg} активировано')
        elif msg == 'все' and options['advanced'] is True:
            for field in advanced_fields.keys():
                options[field] = True
            send_some_message(id, 'Все поля активированы')
        ## Ищем только тех, у кого есть минимум одно дополнительное поле
        elif msg == 'только' and options['advanced'] is True:
            options['only_advanced'] = True
            send_some_message(id, 'Поиск ТОЛЬКО с наличием хотя бы одного дополнительного поля включен')
        ## Начинаем поиск, подключаемся к БД
        elif msg == "поиск":
            print(id, f'Возраст: {from_age}-{to_age}, анкет: {profile_count}, доп.поля - {options["advanced"]}')
            # delete_tables(conn) ## Удалить таблицу, если необходимо
            create_table(conn)  ## Создаем таблицу user + пара, когда пользователь запустил поиск
            attachments = [] ## Для фотографий
            try:
                 for user in get_users(user_id=id)[:profile_count]:  ## кол-во профилей за сессию
                    send_some_message(id, f'{"https://vk.com/id" + str(user[0])} {user[1]} {user[2]}, {user[3]}')
                    if options['advanced'] is True:
                        replace_dict_keys(user)
                        for field in user[4:]:
                            for key, value in field.items():
                                send_some_message(id, f'{key}: {value} \n')
                    for photo_id in get_photos(id=user[0]):
                        attachments.append('photo{}_{}'.format(user[0], photo_id))
                    send_photo(id)
                    attachments.clear()
                    add_user(conn, user_id=id, pair_id=user[0])  ##Добавили пару в БД
            except:
                send_some_message(id, "Ошибка запроса, попробуте позже")
            send_some_message(id, 'Сессия поиска завершена. \n '
                                    'Введите "поиск" повторно (настройки останутся без изменений), '
                                    'либо вы можете изменить количественные параметры (возраст, группы, анкеты). \n'
                                    'Используйте "выход" для завершения работы с ботом (все настройки сбросятся).')
        ## Выход, сбрасываем настройки
        elif msg == "выход":
            print(id, 'вышел из поиска')
            for key, value in options.items():
                options[key] = False
            send_some_message(id, 'До свидания!')
        else:
            send_some_message(id, "Неизвестная команда")

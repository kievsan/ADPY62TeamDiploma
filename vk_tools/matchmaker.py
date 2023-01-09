#  Модуль в разработке

import json
from datetime import date
from pprint import pprint

import requests

import sqlalchemy
import vk_api
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from vk_api.bot_longpoll import VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

import vk_tools
from vk_tools.template import CarouselButtons, Element, Carousel, Button
from vk_tools.vk_bot import VkBot
from filters.standard_filter import StandardFilter, get_standard_filter
from filters.free_user_case_filter import LegitimacyUserFilter
from bot_config.config import get_config
from db_tools import orm_models as orm
from db_tools.orm_models import VKinder, VkIdol
from vk_tools.vk_bot_menu import VkBotMenu


class Matchmaker(VkBot):
    """ Выполняет поиск, показ и сохранение/бан выбранных из подходящих юзверей    """

    def __init__(self, bot='bot.cfg', db='db.cfg'):
        super().__init__(bot)
        self._DB_CONFIG: dict = get_config('db', db)
        self.engine = sqlalchemy.create_engine(self.get_DSN())  # <class 'sqlalchemy.engine.base.Engine'>
        self.SessionLocal = sessionmaker(bind=self.engine)  # <class 'sqlalchemy.orm.session.sessionmaker'>
        self.db: Session = None
        if bool(self._DB_CONFIG['overwrite']):
            orm.drop_tables(self.engine)
        orm.create_tables(self.engine)
        print('A database {} with tables has been created, access is open.'.format(self._DB_CONFIG['dbase name']))

    def get_DSN(self) -> str:
        db = self._DB_CONFIG
        return 'postgresql://{}:{}@{}/{}'.format(db["login"], db["password"], db["server"], db["dbase name"])

    def db_close(self):
        """
        Сохранение в базу и закрытие текущей локальной сессии
        :return: err
        """
        err = ''
        try:
            self.db.commit()
            self.db.close()
        except Exception as err:
            print(err)
            # raise err
        return err

    def add_filter(self, checker: object) -> list:
        filters: list = self.current()['filters']
        filters.append(checker)
        return filters

    def identifying_db_query(self, client_id: int, user_id: int) -> VkIdol:
        return self.db.query(VkIdol).filter(
            VkIdol.vk_id == client_id).filter(
            VkIdol.vk_idol_id == user_id).first()

    def refresh_favorites(self, current):
        """
        Получение списка фаворитов клиента и сохранение списка id фаворитов
        :param current: окружение/данные текущего клиента
        :return: favorites: список фаворитов
        """
        favorites = self.db.query(VkIdol).filter(
            VkIdol.vk_id == current['peer_id'])  # .filter(not VkIdol.ban)  # ???
        current['favorites']['list_ids'] = sorted(idol.vk_idol_id for idol in favorites.all())
        # print('favorite_ids =', current['favorites']['list_ids'])  # ------------------------------------
        return favorites

    def start_favorites_show(self, block_size: int = 10):
        current = self.current()
        menu_: VkBotMenu = current['menu']
        if not self.db:
            self.db = self.SessionLocal()
        # current['client_info']['carousel'] = False  # --------------------------

        max_size = 10 if current['client_info']['carousel'] else 6
        block_size = block_size if 1 <= block_size <= max_size else max_size
        current['favorites']['block_size'] = block_size
        favorites = self.refresh_favorites(current).all()
        if favorites:
            self.event.message['text'] = menu_.services['next']['button']  # 'ВПЕРЁД'
            self.favorites_show_mode_events()
        else:
            self.event.message['text'] = menu_.services['exit']['button']  # 'ВЫХОД'
            self.favorites_show_mode_events()

    def favorites_show_mode_events(self):
        current = self.current()
        menu_: VkBotMenu = current['menu']
        menu = menu_.services
        template_menu = ['Расстаться!']
        client_id = current['peer_id']
        api_fields = 'sex,city,bdate,counters,photo_id,photo_max,_photo_max_origin'

        def get_photo_id(user: dict):
            """
            Получение фото и прикрепление её к сообщению
            :param user: из ответа на api-запрос
            :return: attachment: фото будет передано в сообщение attachment-параметром. Если нет, то ссылкой или ''
            """
            photo_id = user.get('photo_id', '')
            if photo_id:
                return photo_id
            photo_vk_url = user.get('photo_max', '')
            photo_url = photo_vk_url if photo_vk_url else user.get('photo_max_origin', '')
            if photo_url:
                img = requests.get(photo_url, stream=True)
                params = self.vk_upload.photo_messages(img.raw)[0]
                # pprint(params)  # -------------------------------------------
                photo_id = '{}_{}'.format(params['owner_id'], params['id'])
            return photo_id

        def exit_from_favorites_show():
            self.set_empty_favorites()
            self.db_close()
            self.send_msg(message='Просмотр завершен...', keyboard=self.get_keyboard(empty=True))

        def refresh_carousel_of_favorite_users():
            """
            Возвращает следующую карусель избранных пользователей
            :return: user_ids: list(str): список id фаворитов
                   : users_info: dict: словарь со скачанной инфой о фаворитах
            """
            self.refresh_favorites(current)
            block_size = current['favorites']['block_size']
            favorites = current['favorites']
            count_favorites = len(favorites['list_ids'])
            current_block_number = favorites['current_block']['number']
            next_favorite = current_block_number * block_size

            print('Фавориты {} по {}, блок-{}:'.format(
                favorites['list_ids'], block_size, current_block_number))  # ---------------------
            last_favorite = next_favorite + block_size

            if last_favorite > count_favorites:  # --- фаворитов может не хватать на всю карусель
                last_favorite = count_favorites

            #  --- Готовим данные фаворитов для карусели:
            user_ids = list(str(id_) for id_ in favorites['list_ids'][next_favorite:last_favorite])
            users_info = self.vk_api_methods.users.get(
                user_ids=','.join(user_ids), fields=api_fields)
            #  --- Сохраняем данные:
            favorites['current_block'] = {
                'number': current_block_number,
                'user_ids': user_ids,
                'users_info': users_info
            }
            return user_ids, users_info

        def get_next_carousel_of_favorite_users():
            """
            Возвращает следующую карусель избранных пользователей
            :return: user_ids: list(str): список id фаворитов
                   : users_info: dict: словарь со скачанной инфой о фаворитах
            """
            block_size = current['favorites']['block_size']
            favorites = current['favorites']
            count_favorites = len(favorites['list_ids'])
            current_block_number = favorites['current_block']['number']

            if favorites['start']:  # --- если это запуск первой карусели
                print('это запуск первой карусели')
                favorites['start'] = False
                next_favorite = current_block_number * block_size
            else:
                current_block_number += 1  # --- Готовим новую карусель
                next_favorite = current_block_number * block_size
                if next_favorite > count_favorites:  # --- Следующей карусели нет
                    return favorites['current_block']['user_ids'], favorites['current_block']['users_info']
                favorites['previous_block'].put(favorites['current_block'])  # --- сохраним старую карусель

            print('Фавориты {} по {}, блок-{}:'.format(
                favorites['list_ids'], block_size, current_block_number))  # ---------------------
            last_favorite = next_favorite + block_size

            if last_favorite > count_favorites:  # --- фаворитов может не хватать на всю карусель
                last_favorite = count_favorites

            #  --- Готовим данные фаворитов для карусели:
            user_ids = list(str(id_) for id_ in favorites['list_ids'][next_favorite:last_favorite])
            users_info = self.vk_api_methods.users.get(
                user_ids=','.join(user_ids), fields=api_fields)
            #  --- Сохраняем данные:
            favorites['current_block'] = {
                'number': current_block_number,
                'user_ids': user_ids,
                'users_info': users_info
            }
            return user_ids, users_info

        def get_previous_carousel_of_favorite_users():
            """
            Возвращает предыдущую карусель избранных пользователей
            :return: carousel
            """
            current_block = current['favorites']['current_block']
            if not current['favorites']['previous_block'].empty():
                current['favorites']['current_block'] = current['favorites']['previous_block'].get()
                current_block = current['favorites']['current_block']
            return current_block['user_ids'], current_block['users_info']

        def is_ban(client_id_: int, user_id_: int):
            return 'БАН' if self.identifying_db_query(client_id=client_id_, user_id=int(user_id_)).ban else ''

        def create_template(carousel_menu: list,
                            get_carousel=get_next_carousel_of_favorite_users) -> json:
            user_ids, users_info = get_carousel()
            print(f'\t{user_ids}')  # ----------------------------------
            template = list()
            for id_, user in zip(user_ids, users_info):
                city = user.get('city', {})
                template_element = Element(
                    title='{} {}'.format(user['first_name'], user['last_name']),
                    description='{} {} {}\n\tid={}   {}'.format(
                        'жен.' if user['sex'] == 1 else 'муж.',
                        user.get('bdate', ''),
                        city['title'] if city else '',
                        id_,
                        is_ban(client_id, id_)),
                    link=f'https://vk.com/id{id_}',
                    buttons=CarouselButtons(button_labels=carousel_menu, button_id=id_).add_buttons()
                )
                template.append(template_element)
            # pprint(template)  # ---------------------------------------------
            carousel = Carousel(template).add_carousel()
            return carousel

        def create_favorite_users_list_as_link_keyboard(get_carousel=get_next_carousel_of_favorite_users):
            user_ids, users_info = get_carousel()
            print(f'\t{user_ids}')  # ----------------------------------
            keyboard = {"one_time": False, "inline": True, "buttons": []}
            for id_, user in zip(user_ids, users_info):
                id_info = "(id={} {})".format(id_, is_ban(client_id, id_)).strip()
                user_name = f"{user['last_name']} {user['first_name']}"[:25 - len(id_info)]
                button_text = "{} {}".format(user_name, id_info)
                button_link = f"https://vk.com/id{id_}"
                button = Button(button_type='open_link', label=button_text, link=button_link, payload={'user_id': id_})
                # print(button)  # ----------------------------------
                keyboard['buttons'].append([button])
            # pprint(keyboard)  # ---------------------------------------
            keyboard = json.dumps(keyboard, ensure_ascii=False).encode('utf-8')
            return keyboard.decode('utf-8')

        ###

        title = 'Список избранных'

        last_bot_msg_id = str(menu_.service['last_bot_msg_id'] if menu_.service.get('last_bot_msg_id', 0) else '')

        if self.event.type == VkBotEventType.MESSAGE_NEW:
            msg_id = self.event.message.get('id', 0)
            self.print_message_description(msg_id)
            text = current['msg']['text']
            # Oтветы:
            try:
                if self.event.from_chat:
                    self.send_msg_use_bot_dialog()
                elif text == menu['back']['command'].lower() or text == menu['back']['button'].lower():
                    self.del_post(last_bot_msg_id)
                    if current['client_info']['carousel']:
                        self.send_msg(peer_id=client_id,
                                      template=create_template(template_menu, get_previous_carousel_of_favorite_users),
                                      message='{}\t(id={})\n\t{}'.format(
                                          self.get_user_name(client_id), client_id, title))
                    else:
                        self.send_msg(peer_id=client_id,
                                      keyboard=create_favorite_users_list_as_link_keyboard(
                                          get_previous_carousel_of_favorite_users),
                                      message='{}\t(id={})\n\t{}'.format(
                                          self.get_user_name(client_id), client_id, title))
                elif text == menu['next']['command'].lower() or text == menu['next']['button'].lower():
                    self.del_post(last_bot_msg_id)
                    if current['client_info']['carousel']:
                        self.send_msg(peer_id=client_id,
                                      template=create_template(template_menu),
                                      message='{}\t(id={})\n\t{}'.format(
                                          self.get_user_name(client_id), client_id, title))
                    else:
                        self.send_msg(peer_id=client_id,
                                      keyboard=create_favorite_users_list_as_link_keyboard(),
                                      message='{}\t(id={})\n\t{}'.format(
                                          self.get_user_name(client_id), client_id, title))
                elif text == menu['exit']['button'].lower() or text == menu['exit']['command'].lower():
                    self.del_post(last_bot_msg_id)
                    exit_from_favorites_show()
                    self.exit(inline=True)
                elif current['client_info']['carousel'] and text in (command.lower() for command in template_menu):
                    if text == template_menu[0].lower():  # удалить:
                        payload = json.loads(self.event.message.get('payload', '{}'))  # messagePayload
                        user_id = int(payload.get('user_id', '0')) if payload else 0
                        if user_id:
                            print(f'Удаляем id{user_id}')  # ---------------------
                            user_being_deleted = self.identifying_db_query(client_id=client_id, user_id=user_id)
                            if user_being_deleted:
                                self.db.delete(user_being_deleted)
                                self.del_post(last_bot_msg_id)
                                self.send_msg(
                                    peer_id=client_id,
                                    template=create_template(template_menu, refresh_carousel_of_favorite_users),
                                    message='{}\t(id={})\n\t{}'.format(
                                        self.get_user_name(client_id), client_id, title))
                            else:
                                print(f'id{user_id} в БД не найден!')  # ---------------------
                else:
                    if not self.event.from_chat:
                        # self.del_post(last_bot_msg_id)
                        self.start_mode(message='Не понимаю...')
            except KeyError as key_err:
                self.my_except(key_err, f'Попытка взять значение по ошибочному ключу {key_err}'
                                        f' в favorites_show_mode_events', menu)
                raise key_err
            except Exception as other:
                self.my_except(other)
                raise other

        elif self.event.type == VkBotEventType.MESSAGE_REPLY:
            msg_id = self.event.obj.get('id', 0)
            text = self.event.obj['text'].lower()
            if ('текущий' in text) or (title.lower() in text):
                menu_.service['last_bot_msg_id'] = msg_id
                print(f"\nСообщение-{self.event.obj['id']} "
                      f"от бота для {self.event.obj.peer_id}:\n\t{text}")

    def start_search_team(self, client_id: int, search_filter: dict):  # search_advisable_users
        """
        Создание поисковой команды. Подключение необходимых фильтров и интерфейса
        :param client_id:   vk_id собеседника бота, который ищет подходящих пользователей VK
        :param search_filter:   условия стандартного поиска
        :return:
        """
        menu_: VkBotMenu = self.current()['menu']

        if not self.db:
            self.db = self.SessionLocal()
        old_client = self.db.query(VKinder).filter(VKinder.vk_id == client_id).first()
        if not old_client:
            print(f'Новый клиент {client_id}!')
            self.db.add(VKinder(vk_id=client_id, first_visit_date=date.today()))

        chosen_vk_users = self.db.query(VkIdol).filter(VkIdol.vk_id == client_id)
        ban = chosen_vk_users.filter(VkIdol.ban)
        is_free = LegitimacyUserFilter(user_ids=list(user.vk_idol_id for user in chosen_vk_users),
                                       ban_ids=list(ban_user.vk_idol_id for ban_user in ban),
                                       client_id=client_id)
        self.add_filter(is_free)
        print(is_free)

        #        ----------  Стандартный поиск  -----------
        bot_filter: dict = get_standard_filter(search_filter=search_filter)
        print('\n------ {}:\t'.format(search_filter['standard']['description'].strip().upper()), end='')
        if bot_filter['buttons']:
            print(bot_filter['buttons'])
            is_standard = StandardFilter(client_id=client_id, search_filter=search_filter,
                                         api_methods=self.vk_api_methods)
            self.add_filter(is_standard)
            print(is_standard)
        else:
            print('Стандартный фильтр не задан...')

        #   ----------  Поиск по интересам  -----------
        #   InterestChecker
        #
        #   ----------  Продвинутый поиск  -----------
        #   AdvancedChecker
        #

        for service in menu_.services:
            menu_.services[service]['link'] = ''
            menu_.services[service]['payload'] = ''

        menu_.service['last_one_found_id'] = 0
        self.event.message['text'] = menu_.services['next']['button']  # 'СЛЕДУЮЩИЙ'
        self.works_search_team()

    def works_search_team(self, requests_block=10, requests_step=1):  # search_advisable_mode_events
        """
        Поиск (прогон по фильтрам), просмотр и выбор подходящих и забаненных пользователей
        :param requests_block:  кол-во пользователей в api-запросах
        :param requests_step:   шаг проверяемых в блоке api-запроса
        :return:                user (из полученного json)
        :def
        :check_user(user: dict) -> bool:    Работа фмльтров (подходит ли пользователь по выбранным условиям)
        :db_close():                        Сохранение в базу и закрытие текущей локальной сессии
        :get_foto_attachment(user: dict):   Получение фото и прикрепление её к сообщению
        :get_next_user() -> dict:           Возвращает следующего подходящего пользователя VK, или прекращает поиск
        """

        menu_: VkBotMenu = self.current()['menu']
        menu = menu_.services
        client_id = self.current()['peer_id']
        # api_fields = 'sex,city,home_town,bdate,counters,photo_id,photo_max,_photo_max_origin,crop_photo,has_photo,photo_100,photo_200,photo_200_orig,photo_400_orig,photo_50'
        api_fields = ('sex,city,home_town,bdate,counters,' +
                      'photo_id,photo_max,_photo_max_origin,' +
                      'crop_photo,has_photo,' +
                      'photo_100,' +
                      'photo_200,photo_200_orig,' +
                      'photo_400_orig,' +
                      'photo_50')

        def check_user(user: dict) -> bool:
            """
            Работа фмльтров (подходит ли пользователь по выбранным условиям)
            :param user: из json
            :return:    True, если подходит по всем условиям
            """
            filters: list = self.current()['filters']
            for filter_ in filters:
                if not filter_.is_advisable_user(user):
                    return False
            return True

        def exit_from_search_team():
            self.current()['filters'] = []
            menu_.service['last_one_found_id'] = 0
            self.db_close()
            for service in menu_.services:
                menu_.services[service]['link'] = ''
                menu_.services[service]['payload'] = ''
            self.send_msg(message='Поиск завершен...', keyboard=self.get_keyboard(empty=True))

        def get_user_photos(user: dict, album_id: str = 'profile'):
            """
            Поиск фотографий пользователя методом photos.get и сервис-токеном.
            Фото берется сначала из данных, полученных из vk_api методом user.get.
            Затем ищутся фото в профиле пользователя методом photos.get.
            :param user: инфа пользователя, полученная из vk_api методом user.get
            :param album_id:
            :return: количество фото и их список взяты из профиля (альбом 'profile')
            """
            url = 'https://api.vk.com/method/photos.get'
            params = {'owner_id': user['id'],
                      'album_id': album_id,  # служебные: 'profile', 'wall'
                      'access_token': self._BOT_CONFIG['service_token'],
                      'v': '5.131'}
            res = requests.get(url, params=params).json()
            # pprint(res)  # ----------------------------------
            response = res.get('response', {})
            user_photos_count: int = response.get('count', 0)
            user_photos: list = response.get('items', [])
            err = {} if user_photos_count else response.get('error', {})
            if err:
                print(f'\t{err.get("error_msg", "")} (err{err.get("error_code", "")})')  # ---------------------------
            return user_photos_count, user_photos

        def get_foto_attachment(photo_url_1: str = '', photo_url_2: str = '', photo_id: str = ''):
            """
            Получение фото и прикрепление её к сообщению
            :param photo_id:
            :param photo_url_1:
            :param photo_url_2:
            :return: attachment: фото будет передано в сообщение attachment-параметром. Если нет, то ссылкой или ''
            """
            print(f'\t\tphoto_id: {photo_id}' if photo_id else '')  # -------------------------------------
            if not photo_url_1 + photo_url_2 + photo_id:
                return ''
            photo_url = photo_url_1 if photo_url_1 else photo_url_2
            if photo_url:
                img = requests.get(photo_url, stream=True)
                photo = img.raw
                try:
                    params = self.vk_upload.photo_messages(photo)[0]
                    # pprint(params)  # -------------------------------------------
                    attachment = 'photo{}_{}_{}'.format(
                        params['owner_id'], params['id'], params['access_key'])
                except vk_api.exceptions.ApiError as err:
                    print(err)
                    attachment = photo_id
            else:
                attachment = photo_id
            return attachment

        def get_photo_attachment(user: dict):
            attachment = []
            for size in ['max', '400', '200', '100', '50']:
                photo = get_foto_attachment(user.get(f'photo_{size}', ''),
                                            user.get(f'photo_{size}_origin', ''),
                                            user.get('photo_id', ''))
                if photo:
                    attachment.append(photo)
                    break

            if not user.get('has_photo', 0):
                print('\tФотографий в профиле не найдено!')
            else:
                user_photos_count, user_photos = get_user_photos(user)
                print(f'\tНайдено {user_photos_count} фото в профиле!')
                for photo in user_photos:
                    max_size_photo: dict = max((size_photo for size_photo in photo['sizes']),
                                               key=lambda size: size['height'] + size['width'], default=0)
                    if max_size_photo:
                        photo_url = max_size_photo['url']
                        photo_id = f'{user["id"]}_{photo["id"]}'
                        if photo_id != user["photo_id"]:
                            attachment.append(get_foto_attachment(photo_url, '', photo_id))
                        if len(attachment) == 3:
                            break
            return ','.join(attachment)

        def get_next_user() -> dict:
            """
            Возвращает следующего подходящего пользователя VK, или выходит из текущего режима
            :return: user (из полученного json)
            """
            last_id = menu_.service['last_one_found_id']
            number_block = 0
            while True:
                next_id_block = ','.join(str(next_id) for next_id in range(
                    last_id + 1, last_id + requests_block, requests_step))
                users = self.vk_api_methods.users.get(user_ids=next_id_block, fields=api_fields)
                if not users:
                    print('\tПоздравляем, ты всех перебрал, кто подходил под твои условия!')
                    self.current()['filters'] = []
                    self.db_close()
                    return {}
                for user in users:
                    if check_user(user):
                        menu_.service['last_one_found_id'] = user['id']
                        menu_.services['vk_user_page']['link'] = f"https://vk.com/id{user['id']}"
                        menu_.services['vk_user_page']['payload'] = {'user_id': user['id']}
                        self.send_msg(peer_id=client_id, keyboard=self.get_keyboard(inline=True),
                                      message='Нашли {}'.format(self.get_user_title(user_id=user["id"])),
                                      attachment=get_photo_attachment(user))
                        return user
                last_id += requests_step
                number_block += 1
                if number_block % 20 == 0:
                    self.send_msg(message='Терпение! Идёт поиск подходящих пиплов...')

            ###

        if self.event.type == VkBotEventType.MESSAGE_NEW:
            msg_id = self.event.message.get('id', 0)
            self.print_message_description(msg_id)
            last_bot_msg_id = str(menu_.service.get('last_bot_msg_id', ''))
            text = self.event.message['text'].lower()
            user_id = menu_.service['last_one_found_id']
            # Oтветы:
            try:
                if self.event.from_chat:
                    self.send_msg_use_bot_dialog()
                elif text == menu['next']['command'].lower() or text == menu['next']['button'].lower():
                    # self.del_post(del_msg_ids=str(self.event.message['id']))  # удалить user msg  - не работает
                    self.del_post(last_bot_msg_id)
                    if not get_next_user():
                        exit_from_search_team()
                        self.exit()
                elif text == menu['save']['command'].lower() or text == menu['save']['button'].lower():
                    self.db.add(VkIdol(vk_idol_id=user_id, vk_id=client_id, ban=False, rec_date=date.today()))
                    self.del_post(last_bot_msg_id)
                    if not get_next_user():
                        exit_from_search_team()
                        self.exit()
                elif text == menu['ban']['command'].lower() or text == menu['ban']['button'].lower():
                    self.db.add(VkIdol(vk_idol_id=user_id, vk_id=client_id, ban=True, rec_date=date.today()))
                    self.del_post(last_bot_msg_id)
                    if not get_next_user():
                        exit_from_search_team()
                        self.exit()
                elif text == menu['exit']['button'].lower() or text == menu['exit']['command'].lower():
                    self.del_post(last_bot_msg_id)
                    exit_from_search_team()
                    self.exit(inline=True)
                elif text == menu['vk_user_page']['button'].lower() or text == menu['vk_user_page']['command'].lower():
                    self.del_post(last_bot_msg_id)
                    exit_from_search_team()
                    self.exit(inline=True)
                else:
                    if not self.event.from_chat:
                        self.del_post(last_bot_msg_id)
                        self.start_mode(message='Не понимаю...')
            except KeyError as key_err:
                self.my_except(key_err, f'Попытка взять значение по ошибочному ключу {key_err}'
                                        f' в search_advisable_mode_events', menu)
                raise key_err
            except Exception as other:
                self.my_except(other)
                raise other

        elif self.event.type == VkBotEventType.MESSAGE_REPLY:
            msg_id = self.event.obj.get('id', 0)
            text = self.event.obj['text'].lower()
            if 'нашли' in text:
                menu_.service['last_bot_msg_id'] = msg_id
                print(f"\nСообщение-{self.event.obj['id']} "
                      f"от бота для {self.event.obj.peer_id}:\n\t{text}")

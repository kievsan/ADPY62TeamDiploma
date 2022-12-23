#  Модуль в разработке

from datetime import date
from pprint import pprint

import requests

import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from vk_api.bot_longpoll import VkBotEventType
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
        self.filters = []
        # self.client_id = None
        self.chosen_vk_users = None
        if bool(self._DB_CONFIG['overwrite']):
            orm.drop_tables(self.engine)
        orm.create_tables(self.engine)
        print('A database {} with tables has been created, access is open.'.format(self._DB_CONFIG['dbase name']))

    def get_DSN(self) -> str:
        db = self._DB_CONFIG
        return 'postgresql://{}:{}@{}/{}'.format(db["login"], db["password"], db["server"], db["dbase name"])

    def add_filter(self, checker: object) -> list:
        self.filters.append(checker)
        return self.filters

    def start_search_team(self, client_id: int, search_filter: dict):  # search_advisable_users
        """
        Создание поисковой команды. Подключение необходимых фильтров и интерфейса
        :param client_id:   vk_id собеседника бота, который ищет подходящих пользователей VK
        :param search_filter:   условия стандартного поиска
        :return:
        """
        menu_: VkBotMenu = self.current()['menu']
        client_id = self.get_event_peer_id()

        if not self.db:
            self.db = self.SessionLocal()
        old_client = self.db.query(VKinder).filter(VKinder.vk_id == client_id).first()
        if not old_client:
            print(f'Новый клиент {client_id}!')
            self.db.add(VKinder(vk_id=client_id, first_visit_date=date.today()))

        self.chosen_vk_users = self.db.query(VkIdol).filter(VkIdol.vk_id == client_id)
        ban = self.chosen_vk_users.filter(VkIdol.ban)
        self.add_filter(LegitimacyUserFilter(user_ids=list(user.vk_idol_id for user in self.chosen_vk_users),
                                             ban_ids=list(ban_user.vk_idol_id for ban_user in ban),
                                             client_id=client_id))

        #        ----------  Стандартный поиск  -----------
        bot_filter: dict = get_standard_filter(search_filter=search_filter)
        print('\n------ {}:\t'.format(search_filter['standard']['description'].strip().upper()), end='')
        if bot_filter['buttons']:
            print(bot_filter['buttons'])
            self.add_filter(StandardFilter(client_id=client_id, search_filter=search_filter,
                                           api_methods=self.vk_api_methods))
        else:
            print('Стандартный фильтр не задан...')

        #   ----------  Поиск по интересам  -----------
        #   InterestChecker
        #
        #   ----------  Продвинутый поиск  -----------
        #   AdvancedChecker
        #

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
        client_id = self.get_event_peer_id()
        api_fields = 'sex,city,bdate,counters,photo_id,photo_max,_photo_max_origin'

        def check_user(user: dict) -> bool:
            """
            Работа фмльтров (подходит ли пользователь по выбранным условиям)
            :param user: из json
            :return:    True, если подходит по всем условиям
            """
            for filter_ in self.filters:
                if not filter_.is_advisable_user(user):
                    return False
            return True

        def db_close():
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

        def get_foto_attachment(user: dict):
            """
            Получение фото и прикрепление её к сообщению
            :param user: из ответа на api-запрос
            :return: attachment: фото будет передано в сообщение attachment-параметром. Если нет, то ссылкой или ''
            """
            photo_vk_url = user.get('photo_max', '')
            photo_url = photo_vk_url if photo_vk_url else user.get('photo_max_origin', '')
            if photo_url:
                img = requests.get(photo_url, stream=True)
                params = self.vk_upload.photo_messages(img.raw)[0]
                attachment = 'photo{}_{}_{}'.format(
                    params['owner_id'], params['id'], params['access_key'])
            else:
                attachment = user.get('photo_id', '')
            return attachment

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
                    db_close()
                    return {}
                for user in users:
                    if check_user(user):
                        menu_.service['last_one_found_id'] = user['id']
                        # last_bot_msg_id = menu_.service.get('last_bot_msg_id', 0)
                        # if last_bot_msg_id:
                        #     self.del_post(last_bot_msg_id)
                        #     self.send_msg(peer_id=self.client_id, keyboard=self.get_keyboard(inline=True),
                        #                   message='Нашли {}'.format(self.get_user_title(user_id=user["id"])),
                        #                   attachment=get_foto_attachment(user), edit_msg_id=last_bot_msg_id)
                        # else:
                        self.send_msg(peer_id=client_id, keyboard=self.get_keyboard(inline=True),
                                      message='Нашли {}'.format(self.get_user_title(user_id=user["id"])),
                                      attachment=get_foto_attachment(user))
                        return user
                last_id += requests_step
                number_block += 1
                if number_block % 20 == 0:
                    self.send_msg(message='Терпение! Идёт поиск подходящих пиплов...')

            ###

        if self.event.type == VkBotEventType.MESSAGE_NEW:
            msg_id = self.event.message.get('id', 0)
            self.print_message_description(msg_id)
            msg_id = menu_.service.get('last_bot_msg_id', 0)
            text = self.event.message['text'].lower()
            user_id = menu_.service['last_one_found_id']
            # Oтветы:
            try:
                if self.event.from_chat:
                    self.send_msg_use_bot_dialog()
                elif text == menu['next']['command'].lower() or text == menu['next']['button'].lower():
                    if msg_id:
                        # self.del_post(del_msg_ids=str(self.event.message['id']))  # удалить user msg  - не работает
                        self.del_post(del_msg_ids=str(msg_id))  # удалить msg бота
                    if not get_next_user():
                        self.exit()
                elif text == menu['save']['command'].lower() or text == menu['save']['button'].lower():
                    self.db.add(VkIdol(vk_idol_id=user_id, vk_id=client_id, ban=False, rec_date=date.today()))
                    if not get_next_user():
                        self.exit()
                    if msg_id:
                        # self.del_post(del_msg_ids=str(self.event.message['id']))
                        self.del_post(del_msg_ids=str(msg_id))
                elif text == menu['ban']['command'].lower() or text == menu['ban']['button'].lower():
                    self.db.add(VkIdol(vk_idol_id=user_id, vk_id=client_id, ban=True, rec_date=date.today()))
                    if msg_id:
                        # self.del_post(del_msg_ids=str(self.event.message['id']))
                        self.del_post(del_msg_ids=str(msg_id))
                    if not get_next_user():
                        self.exit()
                elif self.exit():
                    db_close()

                else:
                    if not self.event.from_chat:
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
                      f"от бота для {self.event.obj.peer_id}")

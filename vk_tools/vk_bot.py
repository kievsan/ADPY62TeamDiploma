#

import queue
from random import randrange
from pprint import pprint

import requests
import vk_api
from vk_api import VkUpload
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType, VkBotMessageEvent
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id

from bot_config.config import get_config
from vk_tools.vk_bot_menu import VkBotMenu
from filters.standard_filter import get_standard_filter


def split_str_to_list(string=' ', splitter=','):
    return list(c.strip() for c in string.strip().split(splitter))


def filter_switch(switch_filter, filter_2):
    if switch_filter['filter'] and filter_2['filter']:
        switch_filter['filter'] = ''
        filter_2['filter'] = ''
    if not switch_filter['filter'] and filter_2['filter']:
        filter_2['filter'] = ''
    else:
        switch_filter['filter'] = not switch_filter['filter']


def filter_switch_2(switch_filter, filter_2, filter_3):
    if switch_filter['filter'] and filter_2['filter'] and filter_3['filter']:
        switch_filter['filter'] = ''
        filter_2['filter'] = ''
        filter_3['filter'] = ''
    if not switch_filter['filter'] and filter_2['filter'] and filter_3['filter']:
        filter_2['filter'] = ''
        filter_3['filter'] = ''
    else:
        switch_filter['filter'] = not switch_filter['filter']


class VkBot:
    """
    _BOT_CONFIG: dict: Настройки бота из 'bot.cfg'
    group_id :  id бота
    conversations : dict Окружение клиентов бота в многопользовательской среде - беседа, меню, избранные и пр.
    vk_session : vk_api.vk_api.VkApi Сессия api vk по токену.
                                    Используем внешний vk_api модуль для организации работы бота.
    vk_upload : VkUpload(vk_session) : upload сервис
    longpoll : обработчик событий ботом
    event : VkBotMessageEvent dict : текущее Событие
    vk_tools : vk_api.tools.VkTools : пул инструментов vk_api
    vk_api_methods : vk_api.vk_api.VkApiMethod : requests-Методы
    """
    # виды callback-кнопок
    __callback_types__ = ("show_snackbar", "open_link", "open_app")

    def __init__(self, bot='bot.cfg'):
        self._BOT_CONFIG: dict = get_config()
        self.group_id = self._BOT_CONFIG['group_id']
        self.conversations = {}
        self.vk_session = vk_api.VkApi(token=self._BOT_CONFIG['group_token'])  # vk_api.vk_api.VkApi
        self.vk_upload = VkUpload(self.vk_session)
        self.longpoll = VkBotLongPoll(self.vk_session, group_id=self.group_id)
        self.event: VkBotMessageEvent = {}
        self.vk_tools = vk_api.VkTools(self.vk_session)  # vk_api.tools.VkTools
        self.vk_api_methods = self.vk_session.get_api()  # vk_api.vk_api.VkApiMethod
        print(f"Создан объект бота! (id={self.vk_session.app_id})")

    def get_keyboard(self, callback=False, inline=False, one_time=False, empty=False) -> dict:
        """
        Клавиатура нового сообщения бота
        :param callback: подключить callback-кнопки
        :param inline: клавиатура непосредственно в поле диалога / под диалогом
        :param one_time: одноразовая клавиатура
        :param empty: пустая клавиатура
        :return: клавиатура бота
        """
        keyboard = VkKeyboard(inline=inline, one_time=False if inline else one_time)
        if empty:
            return keyboard.get_empty_keyboard()
        buttons = self.current()['menu'].get_buttons()
        buttons_peer_line = 0
        for num, button in enumerate(buttons['buttons']):
            if num and buttons['max'] and num % buttons['max'] == 0:
                keyboard.add_line()
                buttons_peer_line = 0
            else:
                buttons_peer_line += 1
            if buttons_peer_line < 4:
                link = buttons['links'][num]
                payload = buttons['payloads'][num]
                if callback:
                    pass
                else:
                    if link:
                        keyboard.add_openlink_button(button, link, payload)
                    else:
                        keyboard.add_button(
                            button, VkKeyboardColor.NEGATIVE if buttons['filter'][num] else VkKeyboardColor.PRIMARY,
                            payload)
            else:
                print('Слишком много кнопок для одной строки!')
                break
        # pprint(keyboard.get_keyboard())  # ---------------------------------------
        return keyboard.get_keyboard()

    def start(self):
        '''
        Работа с сообщениями
        События будут обработаны в зависимости от текущего режима диалога клиента и бота
        '''
        # Работа с сообщениями
        while True:
            print('Запущен бот группы id =', self.longpoll.group_id)
            try:
                for event in self.longpoll.listen():
                    self.event = event
                    current = self.current()
                    menu = current['menu'].service_name
                    if current['start']:
                        current['client_info'] = current['msg'].get('client_info', {})
                        # pprint(current['client_info'])  # ----------------------------------
                        self.send_msg(message='Моя прелесть...', keyboard=self.get_keyboard(empty=True))
                        current['start'] = 0

                    if menu == 'start-up':
                        self.start_mode_events()
                    elif menu == 'matchmaker':
                        self.matchmaker_mode_events()
                    elif menu == 'search':
                        self.search_mode_events()
                    elif menu == 'print':
                        self.favorites_show_mode_events()
                    elif menu == 'filter':
                        self.search_filter_mode_events()
                    elif menu == 'standard':
                        self.search_standard_filter_mode_events()
                    elif menu == 'advisable':
                        self.works_search_team()
                    else:
                        self.start_mode_events()
            except requests.exceptions.ReadTimeout as timeout:
                for conv in self.conversations:
                    conv['start'] = 1
                continue

    def search_standard_filter_mode_events(self):
        menu_: VkBotMenu = self.current()['menu']
        menu = menu_.services
        if self.event.type == VkBotEventType.MESSAGE_NEW:
            self.print_message_description()
            text = self.event.message['text'].lower()
            # Oтветы:
            try:
                if self.event.from_chat:
                    self.send_msg_use_bot_dialog()
                elif text == menu['male']['command'].lower() or text == menu['male']['button'].lower():
                    filter_switch(menu['male'], menu['female'])
                    self.start_mode(message='Ok,\n{}!'.format(self.get_user_name()))
                elif text == menu['female']['command'].lower() or text == menu['female']['button'].lower():
                    filter_switch(menu['female'], menu['male'])
                    self.start_mode(message='Ok,\n{}!'.format(self.get_user_name()))
                elif text == menu['city']['command'].lower() or text == menu['city']['button'].lower():
                    menu['city']['filter'] = not menu['city']['filter']
                    self.start_mode(message='Ok,\n{}!'.format(self.get_user_name()))
                elif text == menu['younger']['command'].lower() or text == menu['younger']['button'].lower():
                    filter_switch_2(menu['younger'], menu['older'], menu['peers'])
                    self.start_mode(message='Ok,\n{}!'.format(self.get_user_name()))
                elif text == menu['older']['command'].lower() or text == menu['older']['button'].lower():
                    filter_switch_2(menu['older'], menu['younger'], menu['peers'])
                    self.start_mode(message='Ok,\n{}!'.format(self.get_user_name()))
                elif text == menu['peers']['command'].lower() or text == menu['peers']['button'].lower():
                    filter_switch_2(menu['peers'], menu['older'], menu['younger'])
                    self.start_mode(message='Ok,\n{}!'.format(self.get_user_name()))
                elif self.exit():
                    pass
                else:
                    if not self.event.from_chat:
                        self.start_mode(message='Не понимаю...')
                msg = self.send_filter(message='Настроен Фильтр для поиска\t'
                                       )['message'] if menu_.get_filter_string() else ''
            except KeyError as key_err:
                self.my_except(key_err, f'Попытка взять значение по ошибочному ключу {key_err}'
                                        f' в search_standard_filter_mode_events', menu)
                # raise key_err
            except Exception as other:
                self.my_except(other)
                # raise other

    def my_except(self, err: Exception = None, msg='', menu: dict = None):
        if msg:
            print(msg)
        print(err)
        if menu:
            pprint(menu)
        self.exit()

    def search_filter_mode_events(self):
        menu_: VkBotMenu = self.current()['menu']
        menu = menu_.services
        if self.event.type == VkBotEventType.MESSAGE_NEW:
            self.print_message_description()
            last_bot_msg_id = str(menu_.service.get('last_bot_msg_id', ''))
            text = self.event.message['text'].lower()
            # Oтветы:
            try:
                if self.event.from_chat:
                    self.send_msg_use_bot_dialog()
                elif text == menu['standard']['command'].lower() or text == menu['standard']['button'].lower():
                    menu_.switch('standard')
                    self.start_mode(message='Ok,\n{}!'.format(self.get_user_name()))
                elif text == menu['interests']['command'].lower() or text == menu['interests']['button'].lower():
                    self.start_mode(message='Модуль в разработке,\n{}!'.format(self.get_user_name()))
                elif text == menu['advanced']['command'].lower() or text == menu['advanced']['button'].lower():
                    self.start_mode(message='Модуль в разработке,\n{}!'.format(self.get_user_name()))
                elif text == menu['exit']['button'].lower() or text == menu['exit']['command'].lower():
                    self.del_post(last_bot_msg_id)
                    self.send_msg(message='Можно запускать Поиск...', keyboard=self.get_keyboard(empty=True))
                    self.exit(inline=True)
                    std_filter = get_standard_filter(menu)['buttons']
                    print('{}:\t{}'.format(menu_.button,
                                           std_filter if std_filter else 'Стандартный фильтр не задан...'))
                else:
                    if not self.event.from_chat:
                        self.start_mode(message='Не понимаю...')
            except KeyError as key_err:
                self.my_except(key_err, f'Попытка взять значение по ошибочному-1 ключу {key_err}', menu)
            except Exception as other:
                self.my_except(other)
                raise other

        elif self.event.type == VkBotEventType.MESSAGE_REPLY:
            current = self.current()
            if 'текущий' in current['msg']['text']:
                menu_.service['last_bot_msg_id'] = current['msg']['id']
                print(f"\nСообщение-{menu_.service['last_bot_msg_id']} "
                      f"от бота для {current['peer_id']}:\n\t{current['msg']['text']}")
            else:
                print(f"\n\t{current['msg']['text']}\n{self.event.obj['text'].lower()}\n")

    def search_mode_events(self):
        """
        Режим диалога 'Поиск'
        :filter :advisable - доступные режимы
        """
        menu_: VkBotMenu = self.current()['menu']
        menu = menu_.services
        if self.event.type == VkBotEventType.MESSAGE_NEW:
            self.print_message_description()
            last_bot_msg_id = str(menu_.service.get('last_bot_msg_id', ''))
            text = self.event.message['text'].lower()
            # Oтветы:
            try:
                if self.event.from_chat:
                    self.send_msg_use_bot_dialog()
                elif text == menu['filter']['command'].lower() or text == menu['filter']['button'].lower():
                    self.del_post(last_bot_msg_id)
                    menu_.switch('filter')
                    self.start_mode(message='...And hello again,\n{}!'.format(self.get_user_name()))
                elif text == menu['advisable']['command'].lower() or text == menu['advisable']['button'].lower():
                    self.del_post(last_bot_msg_id)
                    search_filter = menu['filter']['services']
                    std_filter = get_standard_filter(search_filter)['buttons']
                    menu_.switch('advisable')
                    menu_.service['last_one_found_id'] = 0
                    self.start_mode(clear_keyboard=True,
                                    message='...And hello again,\n{}!\nИщем по фильтрам\n{}.\t'.format(
                                        self.get_user_name(),
                                        std_filter if std_filter else 'Стандартный фильтр не задан...'))
                    self.send_msg(message='Терпение! Идёт поиск подходящих пиплов...',
                                  attachment='doc49903553_642595119')
                    self.start_search_team(client_id=self.event.message['from_id'], search_filter=search_filter)
                elif text == menu['exit']['button'].lower() or text == menu['exit']['command'].lower():
                    self.del_post(last_bot_msg_id)
                    self.exit(inline=True)
                else:
                    if not self.event.from_chat:
                        self.del_post(last_bot_msg_id)
                        self.start_mode(message='Не понимаю...', inline=True)
            except KeyError as key_err:
                self.my_except(key_err, f'Попытка взять значение по ошибочному-2 ключу {key_err}', menu)
                raise key_err
            except Exception as other:
                self.my_except(other)
                raise other

        elif self.event.type == VkBotEventType.MESSAGE_REPLY:
            current = self.current()
            if 'текущий' in current['msg']['text']:
                menu_.service['last_bot_msg_id'] = current['msg']['id']
                print(f"\nСообщение-{menu_.service['last_bot_msg_id']} "
                      f"от бота для {current['peer_id']}:\n\t{current['msg']['text']}")
            else:
                print(f"\n\t{current['msg']['text']}\n{self.event.obj['text'].lower()}\n")

    def start_search_team(self, client_id, search_filter):
        pass  # реализован у Matchmaker

    def works_search_team(self):
        pass  # реализован у Matchmaker

    def favorites_show_mode_events(self):
        pass  # реализован у Matchmaker

    def matchmaker_mode_events(self):
        """
        Режим диалога Matchmaker
        :search :print - доступные режимы
        """
        menu_: VkBotMenu = self.current()['menu']
        menu = menu_.services

        if self.event.type == VkBotEventType.MESSAGE_NEW:
            self.print_message_description()
            last_bot_msg_id = str(menu_.service.get('last_bot_msg_id', ''))
            text = self.event.message['text'].lower()
            # Oтветы:
            try:
                if self.event.from_chat:
                    self.send_msg_use_bot_dialog()
                elif text == menu['search']['command'].lower() or text == menu['search']['button'].lower():
                    self.del_post(last_bot_msg_id)
                    menu_.switch('search')
                    self.start_mode(message=f'...Together forever,\n{self.get_user_name()}!', inline=True)
                elif text == menu['print']['command'].lower() or text == menu['print']['button'].lower():  # +++++++++
                    self.del_post(last_bot_msg_id)
                    menu_.switch('print')
                    self.start_mode(message=f'...Together forever,\n{self.get_user_name()}!')  # ====
                    self.start_favorites_show()
                    # self.start_mode(message=f'Модуль в разработке,\n{self.get_user_name()}!', inline=True)
                elif text == menu['exit']['button'].lower() or text == menu['exit']['command'].lower():
                    self.del_post(last_bot_msg_id)
                    self.exit(inline=True)
                else:
                    if not self.event.from_chat:
                        self.del_post(last_bot_msg_id)
                        self.start_mode(message='Не понимаю...', inline=True)
            except KeyError as key_err:
                self.my_except(key_err, f'Попытка взять значение по ошибочному ключу {key_err}'
                                        f' в matchmaker_mode_events', menu)
                # raise key_err
            except Exception as other:
                self.my_except(other)
                # raise other

        elif self.event.type == VkBotEventType.MESSAGE_REPLY:
            current = self.current()
            if 'текущий' in current['msg']['text']:
                menu_.service['last_bot_msg_id'] = current['msg']['id']
                print(f"\nСообщение-{menu_.service['last_bot_msg_id']} "
                      f"от бота для {current['peer_id']}:\n\t{current['msg']['text']}")
            else:
                print(f"\n\t{current['msg']['text']}\n{self.event.obj['text'].lower()}\n")

    def start_favorites_show(self):
        print('Модуль в разработке!')

    def start_mode_events(self):
        '''
        Стартовый ("Вежливый") режим диалога
        Бот отвечает на приветствия или прощания
        Бот может переходить в следующий режим Matchmaker по соответствующей команде
         или препираться в сообществе или беседе до бесконечности...
        Команда настраиваются в bot_menu.cfg
        :return:
        '''
        menu_: VkBotMenu = self.current()['menu']
        menu = menu_.services
        greetings = split_str_to_list(self._BOT_CONFIG['greetings'])
        farewells = split_str_to_list(self._BOT_CONFIG['farewells'])
        if self.event.type == VkBotEventType.MESSAGE_NEW:
            self.print_message_description()
            last_bot_msg_id = str(menu_.service.get('last_bot_msg_id', ''))
            text = self.event.message['text'].lower()
            # Oтветы:
            if text:
                if self.event.from_user:
                    # Если клиент пользователя не поддерживает callback-кнопки, нажатие на них будет
                    # отправлять  текстовые сообщения. Т.е. они будут работать как обычные inline кнопки.
                    if "callback" not in self.event.obj.client_info["button_actions"]:
                        print(f'Клиент user_id{self.event.obj.message["from_id"]} не поддерживает callback-кнопки.')
                try:
                    if text in greetings:
                        greeting = greetings[randrange(len(greetings))]
                        message = '{},\n{}!\n :))'.format(greeting.upper(), self.get_user_name())
                        self.start_mode(message=message, inline=True)
                    elif text in farewells:
                        farewell = farewells[randrange(len(farewells))]
                        self.send_msg(message=f'{farewell.upper()},\n{self.get_user_name()}!\n :))')
                    elif text == menu['matchmaker']['command'].lower() or text == menu['matchmaker']['button'].lower():
                        self.del_post(last_bot_msg_id)
                        menu_.switch('matchmaker')
                        self.start_mode(message=f'Спасибо за компанию,\n{self.get_user_name()}!', inline=True)
                        self.send_msg_use_bot_dialog()
                    else:
                        self.del_post(last_bot_msg_id)
                        self.start_mode(message='Не понимаю...', inline=True)
                except KeyError as key_err:
                    self.my_except(key_err, f'Попытка взять значение по ошибочному ключу {key_err}'
                                            f' в start_mode_events', menu)
                    raise key_err
                except Exception as other:
                    self.my_except(other)
                    raise other

        elif self.event.type == VkBotEventType.MESSAGE_REPLY:
            menu_.service['last_bot_msg_id'] = self.event.obj['id']
            print(f'\nНовое сообщение {self.event.obj["id"]}:')
            print('От меня для: ', self.event.obj.peer_id)
            print('Текст:\n', self.event.obj.text.lower())
            print()

        elif self.event.type == VkBotEventType.MESSAGE_TYPING_STATE:
            print('\nПечатает ', end='')
            print(self.event.message['from_id'], end=' ')
            print('для ', end='')
            print(self.event.message['to_id'])
            print()

        elif self.event.type == VkBotEventType.GROUP_JOIN:
            print('\n', self.event.message['from_id'], end=' ')
            print('Вступил в группу!')
            print()

        elif self.event.type == VkBotEventType.GROUP_LEAVE:
            print('\n', self.event.message['from_id'], end=' ')
            print('Покинул группу!')
            print()

        elif self.event.type == VkBotEventType.MESSAGE_EVENT:
            # Callback кнопки не срабатывают: события не происходит ???
            print(self.event.type)
            print()

        else:
            print(self.event.type)
            print()

    def start_mode(self, peer_id='', message='', inline=False, callback=False, clear_keyboard=False):
        """
        Выполняется при переходе в другой режим диалога
        Меняет текущее меню, выводит клавиатуру и соответствующий пост с меню команд нового режима диалога
        :param peer_id:
        :param message:
        :param inline:
        :param callback:
        :param clear_keyboard:
        :return: пост
        """
        menu_: VkBotMenu = self.current()['menu']
        if not peer_id:
            peer_id = self.event.message["peer_id"]
        post = {'peer_id': peer_id, 'random_id': get_random_id(),
                'message': message if self.event.from_chat else f'{message} Текущий{menu_}'}
        if not self.event.from_chat:
            post['keyboard'] = self.get_keyboard(inline=inline, callback=callback, empty=clear_keyboard)
        self.send_post(post)
        return post

    def exit(self, inline=False, callback=False) -> bool:
        """
        Закрытие текущего режима диалога, смена меню, удаление id последнего сообщения бота
        :param inline:
        :param callback:
        :return: успешность операции закрытия текущего режима диалога бота с клиентом
        """
        menu_: VkBotMenu = self.current()['menu']
        menu = menu_.services
        # text = event.text.lower()
        text = self.event.message['text'].lower()
        if text == menu['exit']['button'].lower() or text == menu['exit']['command'].lower():
            if menu_.service.get('last_bot_msg_id'):
                menu_.service['last_bot_msg_id'] = 0
            message = '{},\nсервис "{}" закрыт!'.format(self.get_user_name(), menu_.button)
            menu_.exit()
            self.start_mode(message=message, inline=inline, callback=callback)
            return True
        return False

    def send_filter(self, message=''):
        """" Сообщение пользователю о выбранных фильтрах стандартного поиска подходящих пиплов """
        menu_: VkBotMenu = self.current()['menu']
        std_filter = menu_.get_filter_string()
        message += '\n{}:\t{}'.format(menu_.button, std_filter if std_filter else 'фильтр не задан...')
        post = {'peer_id': self.event.message["peer_id"], 'random_id': get_random_id(), 'message': message,
                'keyboard': self.get_keyboard()}
        self.send_post(post)
        print(message)
        return post

    def send_msg(self, peer_id='', message='', keyboard=None, template=None, attachment='', edit_msg_id=0):
        """" Получает id пользователя ВК <user_id>, и сообщение ему """
        if not peer_id:
            peer_id = self.event.message["peer_id"]
        post = {'peer_id': peer_id, 'random_id': get_random_id(), 'message': message, 'attachment': attachment}
        if keyboard:
            post['keyboard'] = keyboard  # .get_keyboard()
        elif template:
            post['template'] = template  # .create_template()
        self.send_post(post, edit_msg_id)
        return post

    def send_post(self, post, edit_msg_id=0):
        """ Выводит пост, уже подготовленный для метода 'messages.send' """
        try:
            if edit_msg_id:
                post['message_id'] = edit_msg_id
                self.vk_session.method('messages.edit', post)
            else:
                # pprint(post)  # ------------------------------------
                self.vk_session.method('messages.send', post)
        except vk_api.exceptions.ApiError as no_permission:
            print(f'\tfunc "send_post":\t{no_permission}')

    def del_post(self, del_msg_ids: str):
        """ Удаляет пост бота по id поста """
        res_ = {}
        if not del_msg_ids:
            return res_
        try:
            # print(f'\tУдаляются сообщения {del_msg_ids}')  # ------------------------------------
            res = self.vk_api_methods.messages.delete(message_ids=del_msg_ids, delete_for_all=1)
            res_ = sum(res.get(msg_id, 0) for msg_id in res)
            print(f'\tУдалены сообщения {del_msg_ids}' if (res_ == len(res)) else '')  # -------------
        except vk_api.exceptions.ApiError as no_permission:
            print(f'\tfunc "del_post":\t{no_permission}')
        return res_

    def send_msg_use_bot_dialog(self):
        """ Отправляет пост с предложением перейти в личную беседу """
        if not self.event.from_user:
            self.send_msg(message='{} Юзать сервис переходи в чат с @{}!'.format(
                f'{self.get_user_name()}!\n', self._BOT_CONFIG["name"]))

    def print_message_description(self, msg_id=0):
        """ Вывод в консоль Описания сообщения """
        msg_id = str(msg_id) if msg_id else ''
        msg = f'\nНовое сообщение'
        msg += f' {msg_id}' if msg_id else ''
        msg += f'\t{self.event.t}:'
        msg += f'из чата {self.event.chat_id}' if self.event.from_chat else ''
        msg += f'\nот: {self.get_user_title()}'
        msg += f' *--- {self.event.message["text"]}'
        print(msg)
        # print('*---', event.from_user, event.from_chat, event.from_group, event.from_me)
        return msg

    def current(self):
        """ Текущее окружение клиента бота в многопользовательской среде - беседа, меню, избранные и пр. """
        peer_id_, peer_id = self.get_event_peer_id()
        if not peer_id:
            return {}
        if peer_id in self.conversations:
            self.conversations[peer_id]['msg'] = self.get_event_msg()
        else:
            self.conversations[peer_id] = {
                'peer_id': peer_id_,
                'menu': VkBotMenu(),
                'filters': [],
                'favorites': {},
                'msg': self.get_event_msg(),
                'start': 1}
            self.set_empty_favorites()
        return self.conversations.get(peer_id, {})

    def set_empty_favorites(self):
        """ Стартовый 'набор' фаворитов для нового клиента бота """
        current = self.current()
        current['favorites'] = {
            'list_ids': [],
            'block_size': 10,
            'current_block': {
                'number': 0,
                'user_ids': [],
                'users_info': {}
            },
            'previous_block': queue.LifoQueue(),
            'start': True
        }
        return current['favorites']

    def get_event_peer_id(self):
        """ Получить id инициатора текущего события """
        peer_id = 0
        if self.event:
            if self.event.type == VkBotEventType.MESSAGE_NEW:
                peer_id = self.event.message['peer_id']
            elif self.event.type == VkBotEventType.MESSAGE_REPLY:
                peer_id = self.event.obj.peer_id
        return peer_id, str(peer_id) if peer_id else ''

    def get_event_msg(self):
        """ Получить стандартную инфу о текущем событии """
        msg = {}
        if self.event:
            if self.event.type == VkBotEventType.MESSAGE_NEW:
                msg = {'type': self.event.t,
                       'client_info': self.event.client_info,
                       'from_id': self.event.message['from_id'],
                       'id': self.event.message['id'],
                       'cmid': self.event.message['conversation_message_id'],
                       'text': self.event.message['text'].lower()}
            elif self.event.type == VkBotEventType.MESSAGE_REPLY:
                msg = {'type': self.event.t,
                       'from_id': self.event.obj['from_id'],
                       'id': self.event.obj['id'],
                       'cmid': self.event.obj['conversation_message_id'],
                       'text': self.event.obj['text'].lower()}
        return msg

    def get_user(self, user_id='', name_case='nom', fields="city"):
        """ Получаем пользователя """
        if not user_id:
            user_id = self.event.message["from_id"]
        return self.vk_api_methods.users.get(user_ids=user_id, fields=fields, name_case=name_case)[0]

    def get_user_name(self, user_id=0, name_case='nom'):
        """ Получаем имя пользователя"""
        if not user_id:
            user_id = self.event.message["from_id"]
        user = self.get_user(user_id=user_id, name_case=name_case)
        return f'{user.get("first_name", "")} {user.get("last_name", "")}'

    def get_user_city(self, user_id=0):
        if not user_id:
            user_id = self.event.message["from_id"]
        user = self.get_user(user_id=user_id)
        return user.get("city", '')

    def get_user_title(self, user_id=0):
        """ Получаем кратко пользователя"""
        if not user_id:
            user_id = self.event.message["from_id"]
        user = self.get_user(user_id=user_id, name_case='gen')
        return f'{user.get("last_name", "")} {user.get("first_name", "")} (id = {user_id})'

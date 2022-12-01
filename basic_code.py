from random import randrange

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

# token = input('Token: ')
with open('token.txt', 'r') as file_object:
    token = file_object.read().strip()
vk = vk_api.VkApi(token=token)  # Авторизуемся как сообщество
longpoll = VkLongPoll(vk)  # Работа с сообщениями


def write_msg(user_id, message):
    """"
    получает id пользователя ВК <user_id>, и сообщение ему
    """
    vk.method('messages.send',
              {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7), })


for event in longpoll.listen():  # Основной цикл событий
    """"
    мы циклически будем проверять на наличие event-ов. А получить тип event-а сможем с помощью event.type.
    После этого получив сообщение от пользователя сможем отправить ему соответствующее письмо с помощью 
    уже созданной функции write_msg.
    Cоздан очень простой бот в ВК с такой же простой реализацией. А логику бота можно программировать как душе угодно.
    """
    if event.type == VkEventType.MESSAGE_NEW:  # Если пришло новое сообщение
        if event.to_me:  # Если оно имеет метку для бота
            request = event.text    # Сообщение от пользователя
            # логика ответа:
            if request == "привет":
                write_msg(event.user_id, f"Хай, {event.user_id}")
            elif request == "пока":
                write_msg(event.user_id, "Пока((")
            else:
                write_msg(event.user_id, "Не поняла вашего ответа...")

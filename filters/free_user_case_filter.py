# Проверяет, есть ли пользователь в списке избранных клиента


class LegitimacyUserFilter:
    """
    Проверяет, есть ли пользователь в списке избранных клиента.
    Если есть, то такой пользователь дальше не рассматривается как подходящий.
    :param user_ids: список id всех пользователей VK, избранных клиентом, включая бан.
    :param ban_ids: список id всех забаненных клиентом пользователей VK.
    :return: bool: прошел проверку - True
    """
    _skill = 'Checking the validity of new users'

    def __init__(self, client_id: int, user_ids: list = [], ban_ids: list = []):
        self.user_ids = user_ids
        self.ban_ids = ban_ids
        self.client_id = client_id
        self.user = {}

    def is_advisable_user(self, user: dict) -> bool:
        self.user = user
        user_id = user['id']
        print(self)
        if user_id in self.user_ids:
            print(f'\t\tuser{user_id} НЕ ПРОШЁЛ:', end=' ')
            print(f'забанен клиентом!' if user_id in self.ban_ids
                  else 'уже в списке избранных!')
            return False
        print('\t\tПРОШЁЛ: еще нет в списке избранных!')
        return True

    def __str__(self):
        return f'\nid={self.user.get("id", "")} (client-{self.client_id}), ' \
               f'users={list(self.user_ids)}, ban={list(self.ban_ids)})'

#
from pprint import pprint
import vk_api

import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
# from fastapi import Depends, FastAPI

from bot_config.config import get_config
from db_tools import orm_models as orm


# app = FastAPI()


def check_dict_keys(dict_, keys, msg='данных'):
    if not dict_ or not keys:
        return []
    for key in keys:
        try:
            dict_ = dict_[key]
        except KeyError as key_err:
            print(f'\nОшибка {msg}: отсутствует ключ {key_err}')
            return []
    return dict_


class Matchmaker:
    def __init__(self, db='db.cfg'):
        self._DB_CONFIG: dict = get_config('db', db)
        self.engine = sqlalchemy.create_engine(self.get_DSN())
        self.SessionLocal = sessionmaker(bind=self.engine)
        if bool(self._DB_CONFIG['overwrite']):
            orm.drop_tables(self.engine)
        orm.create_tables(self.engine)
        print('A database {} with tables has been created, access is open.'.format(self._DB_CONFIG['dbase name']))

    def get_DSN(self) -> str:
        db = self._DB_CONFIG
        return 'postgresql://{}:{}@{}/{}'.format(db["login"], db["password"], db["server"], db["dbase name"])

    #
    # @staticmethod
    # def get_db(session_local):
    #     db = session_local()
    #     try:
    #         yield db
    #     finally:
    #         db.close()

    def search_advisable_users(self, group_id='', client_id='', search_filter={},
                               vk_tools: vk_api.tools.VkTools = None) -> list:
        # db: Session = Depends(Matchmaker.get_db(self.SessionLocal))
        db = self.SessionLocal()
        for user in db.query(orm.Advisable).all():
            db.delete(user)
        Matchmaker.refresh_group_users(db, group_id, vk_tools)
        std_filter = self.get_standard_filter(search_filter)
        if std_filter:

            advisable_users = list(db.query(orm.Advisable).all())
        else:
            advisable_users = list(db.query(orm.Advisable).all())
        db.commit()
        db.close()
        return advisable_users

    def get_standard_filter(self, search_filter={}) -> dict:
        if not search_filter: return {}
        try:
            std_filter: dict = search_filter['standard']['services']
            buttons = list(std_filter[service]['button'] for service in std_filter)
            filters = list(std_filter[service]['filter'] for service in std_filter)
            return {'string': ', '.join(list(button for num, button in enumerate(buttons) if filters[num])),
                    'filter_values': list({'filter': button, 'value': filters[num]}
                                          for num, button in enumerate(buttons) if filters[num])}
        except KeyError as key_err:
            print(f'\nОшибка данных: отсутствует ключ {key_err}')
            return {}
        except Exception as other:
            print(f'\n{other}')
            return {}

    @staticmethod
    def refresh_group_users(db: Session = None, group_id: str = '', vk_tools: vk_api.tools.VkTools = None) -> list:
        if not (db and group_id and vk_tools):
            print('Недостаточно параметров! db, group, tools')
            return []
        # db = self.SessionLocal()
        print('\nRecording new users of VK group...')
        vk_users_added = []
        while True:
            vk_group_users_right_now = vk_tools.get_all('groups.getMembers', 1000, {'group_id': group_id})['items']
            pprint(vk_group_users_right_now)
            vk_users_added += list(vk_id for vk_id in vk_group_users_right_now if
                                   not db.query(orm.VkGroup).filter(orm.VkGroup.vk_id == vk_id).first())
            db.add_all(orm.VkGroup(vk_id=vk_id) for vk_id in vk_users_added)
            print('Added  to the VK group:', vk_users_added if vk_users_added else 'has no new users!')
            break
        db.commit()
        # db.close()
        print('Congratulations! The updated list of users of the group has been read and recorded in the database.')
        return vk_users_added

    def print_advisable(self):
        db = self.SessionLocal()

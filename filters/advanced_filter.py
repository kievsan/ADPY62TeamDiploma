#

from filters.filter import VkUserFilter
from vk_api.vk_api import VkApiMethod


class AdvancedFilter(VkUserFilter):
    _skill = 'An advanced Search Engine of the matchmaker'

    def __init__(self, client_id: int, api_methods: VkApiMethod, search_filter: dict):
        super(AdvancedFilter, self).__init__(client_id, api_methods, search_filter, self._skill)

    def is_advisable_user(self, user: dict) -> bool:
        super(AdvancedFilter, self).is_advisable_user(user)
        return True

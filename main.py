#

from vk_tools.vk_bot import VkBot
import db_tools

if __name__ == '__main__':
    bot = VkBot('bot.cfg')
    bot.start()


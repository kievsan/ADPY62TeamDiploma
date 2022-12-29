import json
from typing import Optional


class Carousel(object):

    def __init__(self, carousel: list):
        self.carousel = carousel

    def add_carousel(self):
        obj = json.dumps({'type': 'carousel', 'elements': self.carousel}, ensure_ascii=False).encode('utf-8')
        return obj.decode('utf-8')


class Element:

    def __new__(cls, title: Optional[str] = None, description: Optional[str] = None,
                photo_id: Optional[str] = None, link: Optional[str] = None,
                buttons: Optional[list] = None, template_type: str = "open_link"):
        if template_type == 'open_link':
            return {
                'title': title,
                'description': description,
                'action': {
                    'type': "open_link",
                    'link': link
                },
                'photo_id': photo_id,
                'buttons': buttons
            }
        elif template_type == 'open_photo':
            return {
                'title': title,
                'description': description,
                'photo_id': photo_id,
                'action': {
                    'type': 'open_photo'
                },
                'buttons': buttons
            }
        else:
            raise ValueError("Parameter template_type has: open_link or open_photo")


class CarouselButtons(object):
    __max__ = 3

    def __init__(self, button_labels: list, button_id: str):
        self.labels = button_labels
        self.button_id = button_id

    def add_buttons(self) -> list:
        if not self.labels or len(self.labels) > self.__max__:
            print("\n\tParameter 'button_labels' has not correct value...")
            return []
        buttons = list(Button(label=label, payload={'user_id': self.button_id}
                              ) for label in self.labels)
        return buttons


class ButtonColor:
    NEGATIVE = 'negative'
    POSITIVE = 'positive'
    PRIMARY = 'primary'
    SECONDARY = 'secondary'


class Button:

    def __new__(cls, button_type: Optional[str] = 'text',
                label: Optional[str] = 'VK',
                color: Optional[str] = ButtonColor.PRIMARY,
                link: Optional[str] = 'https://vk.com',
                payload: Optional[dict] = None):
        if button_type.lower() == 'text':
            obj = Text(label=label, color=color, payload=payload)
        elif button_type.lower() == 'open_link':
            obj = OpenLink(label=label, link=link, payload=payload)
        else:
            print("Parameter button_type has: 'text' or 'open_link'")
            obj = Text(label=label, color=color, payload=payload)
        return obj


class Text:

    def __new__(cls, label: Optional[str] = 'Текст кнопки',
                color: Optional[str] = 'secondary',
                payload: Optional[str] = None):
        print('\twas created Text-button: {}, color: {}'.format(label, color))
        return {'action': {'type': 'text', 'label': label, 'payload': payload},
                'color': color}

    # def __str__(self):
    #     print('\tText-button')


class OpenLink:

    def __new__(cls, label: Optional[str] = 'VK',
                link: Optional[str] = 'https://vk.com',
                payload: Optional[str] = None):
        print('\twas created Link-button: {}, link: {}'.format(label, link))
        return {'action': {'type': 'open_link', 'label': label, 'link': link, 'payload': payload}}

    # def __str__(self):
    #     print('\tLink-button')

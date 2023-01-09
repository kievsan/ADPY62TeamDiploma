# Командный проект по курсу «Профессиональная работа с Python»

## [VKinder](https://vk.com/vkinder10)

[![logo](sticker.png)](https://vk.com/vkinder10)

**Исполнил:** 

> * Сергей Киевский

### Цель проекта

1. разработать программу-бота для взаимодействия с базами данных социальной сети. Бот будет предлагать различные варианты людей для знакомств в социальной сети Вконтакте в виде диалога с пользователем.
1. бонусы:
> - получить практический опыт работы в команде
> - прокачать навыки коммуникации и умение выполнять задачи в срок
> - закрепить навыки работы с GitHub и программирования на языке Python
> - разработать с нуля полноценный программный продукт, который можно будет добавить в портфолио бэкенд-разработчика.

### Задание:
- разработать программу-бота на Python
- спроектировать и реализовать базу данных (БД) для программы
- настроить взаимодействие бота с ВК
- написать документацию по использованию программы

------

### Инструкция к работе над проектом

Необходимо разработать программу-бота, которая должна выполнять следующие действия:
1. Используя информацию (возраст, пол, город) о пользователе, который общается с ботом в ВК, сделать поиск других людей (других пользователей ВК) для знакомств.
2. У тех людей, которые подошли под критерии поиска, получить три самые популярные фотографии в профиле. Популярность определяется по количеству лайков.
3. Выводить в чат с ботом информацию о пользователе в формате:
```
Имя Фамилия
ссылка на профиль
три фотографии в виде attachment(https://dev.vk.com/method/messages.send)
```
4. Должна быть возможность перейти к следующему человеку с помощью команды или кнопки.
5. Сохранить пользователя в список избранных.
6. Вывести список избранных людей.

*Внимание: токен для ВК можно получить выполнив [инструкцию](https://docs.google.com/document/d/1_xt16CMeaEir-tWLbUFyleZl6woEdJt-7eyva1coT3w/edit?usp=sharing).*

------

### Пакет *bot_config*:
1. **config.py**
> Настройки и ключи бота, его меню и базы данных хранятся в трёх cfg файлах >
> *bot.cfg, bot_menu.cfg, db.cfg* , создаваемых или  перезаписываемых config.py

------

### Пакет *db_tools*:
1. **orm_models.py**
> Создаёт БД посредством СУБД **Postgres** ORM **sqlalchemy**. >
> *db.cfg* содержит необходимые для этого настройки.
2. **Vkinder sheme.png**
> Схема БД (*vkinders, vk_idols*). СУБД **Postgres**. ORM **sqlalchemy**.
>> *vkinders*
>> -
> class VKinder:
> - vk_id = Column(Integer, primary_key=True, index=True)   - **Клиент бота**
> - first_visit_date = Column(Date, nullable=False)
>
>> *vk_idols*
>> -
> class VkIdol:
> - id = Column(Integer, primary_key=True, autoincrement=True)
> - vk_idol_id = Column(Integer, nullable=False, index=True)   - **Избранный**
> - vk_id = Column(Integer, ForeignKey('vkinders.vk_id'), primary_key=True)   - **Клиент бота**
> - ban = Column(Boolean, nullable=False)
> - rec_date = Column(Date, nullable=False)
> - idols = relationship(VKinder, backref='vkinders')
> 

------

### Чеклист готовности к работе над проектом

1. Изучили «Инструкцию по выполнению командного проекта» и «Правила работы в команде» в личном кабинете.
1. Знаете, кто с вами в команде.
1. Познакомились со своей командой и определились, каким способом будете общаться (переписка в любом мессенджере, видеозвонки).
1. Договорились, кто будет размещать общий репозиторий проекта и отправлять его на проверку.
1. У вас должен быть установлен Python 3.x и любая IDE. Мы рекомендуем работать с Pycharm.
1. Настроен компьютер для работы с БД PostgreSQL.
1. Установлен git и создан аккаунт на Github.
1. Должна быть создана группа во Вконтакте, от имени которой будет общаться разрабатываемый бот. Инструкцию можно будет посмотреть [здесь](group_settings.md).

Если все этапы чеклиста пройдены, то можете стартовать работу над проектом. Успехов в работе!

------

### Инструменты/ дополнительные материалы, которые пригодятся для выполнения задания

1. [Python](https://www.python.org/) + IDE([Pycharm](https://www.jetbrains.com/ru-ru/pycharm/download))
2. [Git](https://git-scm.com/) + [Github](https://github.com/)
3. [Postgre](https://www.postgresql.org/) + [PgAdmin](https://www.pgadmin.org/)
4. [ВКонтакте](https://vk.com/)

------

### Роадмап и распределение задач в команде

Работа над проектом рассчитана на 10 дней для команды из 2-3 человек. Для планирования своего времени рекомендуется опираться на роадмап. Придерживайтесь следующего деления проекта на этапы и задачи участников:

<details>
  <summary> 1. Вариант для команды из 2 участников</summary>

  ### Роадмап:
  
  ![image](https://github.com/netology-code/adpy-team-diplom/blob/main/%D0%94%D0%BB%D1%8F%20%D0%BA%D0%BE%D0%BC%D0%B0%D0%BD%D0%B4%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BF%D1%80%D0%BE%D0%B5%D0%BA%D1%82%D0%B0_2%20%D1%87%D0%B5%D0%BB.png)
  
### 1 этап:
1. Участник А. Создайте общий репозиторий на github. Для предоставления доступа другим участникам необходимо зайти в `Settings` репозитория проекта, найти раздел `Collaborators`, кликнуть по кнопке `Add people`, добавить ник напарника и выбрать роль `Admin`.
2. Участник Б: Спроектируйте БД. В БД должно быть создано минимум 3 таблицы. 
### 2 этап:
1. Участник А: Разработайте взаимодействие с ВК для получения информации о пользователях и их фотографий. Можно использовать готовые библиотеки.
2. Участник Б: Реализуйте БД для программы с помощью PostgreDB. Приложите скрипты для создания таблиц, чтобы преподаватель смог создать у себя БД. Можно использовать ORM.
### 3 этап:	
1. Участник А: 
  - Разработайте взаимодействие с ботом. Можно воспользоваться этим [шаблоном](basic_code.py). Будет плюсом, если вы добавите кнопки для более удобного взаимодействия с пользователем. 
  - Подготовьте проект к сдаче курсовой работы. Исправьте ошибки.
2. Участник Б: 
  - Реализуйте интеграцию бота и БД. Напишите документацию. 
  - Подготовьте проект к сдаче курсовой работы. Исправьте ошибки.

------
  
</details>

<details>
  <summary> 2. Вариант для команды из 3 участников</summary>
  
   ### Роадмап:
  
  ![image](https://github.com/netology-code/adpy-team-diplom/blob/main/%D0%94%D0%BB%D1%8F%20%D0%BA%D0%BE%D0%BC%D0%B0%D0%BD%D0%B4%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BF%D1%80%D0%BE%D0%B5%D0%BA%D1%82%D0%B0_3%20%D1%87%D0%B5%D0%BB.png)
  
  ### 1 этап:
1. Участник А. Создайте общий репозиторий на github. Для предоставления доступа другим участникам необходимо зайти в `Settings` репозитория проекта, найти раздел `Collaborators`, кликнуть по кнопке `Add people`, добавить ник напарника и выбрать роль `Admin`.
2. Участник Б: Спроектируйте БД. В БД должно быть создано минимум 3 таблицы. 
3. Участник B: Разрабойте взаимодействие с ВК для получения информации о пользователях и их фотографий. Можно использовать готовые библиотеки.
### 2 этап:
1. Участник А: Разрабойте взаимодействие с ботом. Можно воспользоваться этим [шаблоном](basic_code.py). Будет плюсом, если вы добавите кнопки для более удобного взаимодействия с пользователем.
2. Участник Б: Реализуйте БД для программы с помощью PostgreDB. Приложите скрипты для создания таблиц, чтобы преподаватель смог создать у себя БД. Можно использовать ORM.
3. Участник B: Реализуйте интеграцию бота и БД.
### 3 этап:	
1. Участник A: Подготовьте проект к сдаче курсовой работы. Исправьте ошибки.
2. Участник Б: Подготовьте проект к сдаче курсовой работы. Исправьте ошибок.
3. Участник В: Напишите документацию.
    
</details>

-----
  
### Дополнительные требования к проекту (необязательные для получения зачёта)

1. Получать токен от пользователя с нужными правами.
2. Добавлять человека в чёрный список, чтобы он больше не попадался при поиске, используя БД.
3. Создать кнопки в чате для взаимодействия с ботом.
4. Добавить возможность ставить/убирать лайк выбранной фотографии.
5. К списку фотографий из аватарок добавлять список фотографий, где отмечен пользователь.
6. В ВК максимальная выдача при поиске - 1000 человек. Подумать, как это ограничение можно обойти.
7. Можно усложнить поиск, добавив поиск по интересам. Разбор похожих интересов (группы, книги, музыка, интересы) нужно будет провести с помощью анализа текста.
8. У каждого критерия поиска должны быть свои веса, то есть совпадение по возрасту должно быть важнее общих групп, интересы по музыке - важнее книг, наличие общих друзей - важнее возраста и т.д.

------

### Правила сдачи работы

- разработан бот и все части кода объединены в главной ветке (master/main)
- один из участников команды добавил ссылку на публичный репозиторий в личном кабинете в поле «Ссылка на решение» и в поле «Отправить на проверку эксперту» проставил галочку

------

### Критерии оценки

Зачёт по разработанному проекту может быть получен, если созданный программный продукт соответствует следующим критериям:

1. Отсутствуют ошибки (traceback) во время выполнения программы.
2. Результат программы записывается в БД. Количество таблиц должно быть не меньше трех. Приложена схема БД.
3. Программа добавляет человека в избранный список, используя БД.
4. Программа декомпозирована на функции/классы/модули/пакеты.
5. Написана документация по использованию программы.
6. Код программы удовлетворяет PEP8. Перед отправкой решения на проверку проверьте код с помощью линтеров.

Зачёт ставится всем студентам-участникам команды при выполнении всех требований командного проекта

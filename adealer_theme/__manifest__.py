# -*- coding: utf-8 -*-
{
    'name': "3A-dealer Theme",
    # Слово «бекенд» — першим. У каталозі тем більшість карток — теми САЙТУ, і
    # покупець за звичкою читає нашу так само. Сказати це прямо коштує двох
    # слів; дізнатися після встановлення — повернення й одна зірка.
    'summary': "Odoo backend theme: navy & gold, with a collapsible menu "
               "sidebar. Тема бекенду Odoo: navy + gold і бічне меню",
    'description': """
        Тема бекенду Odoo у стилі додатку 3A-dealer:
        верхня панель, меню, кнопки, списки, вкладки, чекбокси.

        Бічне меню: дерево меню поточного застосунку зліва, згортається
        одним кліком. Працює в будь-якому застосунку Odoo.

        Встановлюється/видаляється окремо від модуля adealer.
    """,
    'author': "chukhin",
    "support": "adealer@yellow.in.ua",
    'website': "https://aktiv.in.ua/dodatky/",
    'license': "LGPL-3",
    'category': 'Themes/Backend',
    'version': '19.0.1.2.0',
    # 🔴 Перша картинка — це картка в каталозі. Без ключа `images` картка
    # виходить сірим прямокутником поруч із рештою лінійки, а `index.html` уже
    # посилався на banner.png, якого не було, — тобто сторінка опису
    # відкривалась битим зображенням у самому верху. Ніщо при цьому не падало:
    # модуль ставиться, тести зелені.
    #
    # 🔴 І картинка ВЕРТИКАЛЬНА. Картка теми в магазині — макет вікна браузера,
    # співвідношення ~0.80 (зміряно по десяти опублікованих темах). Перший
    # варіант був горизонтальний, 560x315 як у звичайних додатків, і картка
    # показувала його вузькою смужкою серед білих полів. Збирається
    # `3A/tools/store/make_theme_card.py` із кольорів самої теми.
    'images': ['static/description/banner.png'],
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'adealer_theme/static/src/css/theme.css',
            'adealer_theme/static/src/js/theme_sidebar.js',
            'adealer_theme/static/src/xml/theme_sidebar.xml',
        ],
    },
    'installable': True,
    'application': False,
}

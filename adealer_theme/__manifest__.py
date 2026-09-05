# -*- coding: utf-8 -*-
{
    'name': "3A-dealer Theme",
    'summary': "Фірмова тема 3A-dealer (navy + gold) для всього бекенду Odoo",
    'description': """
        Брендування інтерфейсу Odoo у стилі додатку 3A-dealer:
        верхня панель, меню, кнопки, списки, вкладки, чекбокси.
        Встановлюється/видаляється окремо від модуля adealer.
    """,
    'author': "chukhin",
    "support": "adealer@yellow.in.ua",
    'license': "LGPL-3",
    'category': 'Themes/Backend',
    'version': '19.0.1.1.4',
    # 🔴 Перша картинка — це картка в каталозі. Без ключа `images` картка
    # виходить сірим прямокутником поруч із рештою лінійки, а `index.html` уже
    # посилався на banner.png, якого не було, — тобто сторінка опису
    # відкривалась битим зображенням у самому верху. Ніщо при цьому не падало:
    # модуль ставиться, тести зелені. Банер збирається
    # `3A/tools/store/make_banner_theme.py` із кольорів самої теми.
    'images': ['static/description/banner.png'],
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'adealer_theme/static/src/css/theme.css',
        ],
    },
    'installable': True,
    'application': False,
}

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
    'license': "LGPL-3",
    'category': 'Themes/Backend',
    'version': '19.0.1.1.1',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'adealer_theme/static/src/css/theme.css',
        ],
    },
    'installable': True,
    'application': False,
}

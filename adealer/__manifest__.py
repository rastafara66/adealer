# -*- coding: utf-8 -*-
{
    'name': "3A-dealer — Car Dealership & Service",

    'summary': "Автосалон · Автозапчастини · Авторемонт (СТО) — документообіг у стилі 1С для Odoo",

    'description': """
3A-dealer — вертикальне рішення для автодилерів і СТО
=====================================================

Автосалон, склад автозапчастин та авторемонт (СТО) в одному модулі,
зі звичним для користувачів 1С документообігом.

Основні можливості:

* Ланцюжок документів як у 1С: Замовлення клієнта → Наряд-замовлення →
  Видаткова / Акт / Рахунок (кожен документ «на підставі» попереднього).
* Наряд-замовлення СТО: клієнт, автомобіль (VIN), пробіг, механіки,
  сервісний консультант, запчастини й роботи, контроль залишків.
* Картотека автомобілів клієнтів: VIN, бренд (лого), історія ремонтів,
  календар записів на обслуговування, нагадування про ТО.
* Запчастини та аналоги, нормо-години, виробіток механіків.
* Звіти у двох стилях: «Готові звіти» (як у 1С) та інтерактивний pivot Odoo.
* Друковані форми (UA): рахунок на оплату, видаткова, повернення,
  прибуткова накладна, довіреність, акт звірки взаєморозрахунків.
* Журнали документів у стилі 1С: Дата · Номер · Клієнт · Авто · Сума · Статус.
* Українська локалізація інтерфейсу.
    """,

    'application': True,
    'author': "3A Dealer",
    'website': "https://apps.odoo.com",
    'license': "LGPL-3",
    'category': 'Sales',
    'version': '19.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'mail',
                'stock',
                'sale_management',
                'account',
                'purchase',
                'hr',
                'fleet',
                'maintenance',
                'repair',
                'contacts',
                'crm'
                ],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/partner_child_cleanup_wizard_view.xml',  # <-- цей файл має бути раніше за views.xml!
        'views/addresses_import_wizard.xml',  # <-- цей файл має бути раніше за views.xml!
        'views/partner_import_wizard.xml', # <-- цей файл має бути раніше за views.xml!
        'views/journals.xml',  # <-- журнальні list-view; мають бути раніше за views.xml (actions на них посилаються)
        'views/views.xml',
        'views/templates.xml',
        'views/partner_view.xml',
        'views/vehicles.xml',
        'views/product_template.xml',
        'views/service.xml',
        'data/repair_stage_data.xml',  # стандартні стадії наряду (перед alfa_features)
        'views/alfa_features.xml',  # розширення: нормо-години, стадії, склад авто, кампанії, аналоги
        'views/vehicle_service.xml',  # історія обслуговування + нагадування про ТО
        'views/reports_alfa.xml',  # друковані форми UA: наряд, акт робіт, акт прийому-передачі авто
        'views/reports_ua.xml',  # друковані форми UA: рахунок, видаткова, повернення, прибуткова, довіреність, акт звірки
        'views/sale.xml',
        'views/res_config_settings_views.xml',
        'views/report_partner_balance.xml',
        'views/report_wizards.xml',
        'views/reports.xml',
        'data/cron.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'adealer/static/src/css/report.css',
        ],
        'web.assets_backend': [
            'adealer/static/src/css/custom.css',
            'adealer/static/src/js/custom.js',
            'adealer/static/src/js/adealer_sidebar.js',
            'adealer/static/src/xml/adealer_sidebar.xml',
        ],
    },
    'external_dependencies': {
        'python': ['pandas', 'openpyxl'],
    },
}

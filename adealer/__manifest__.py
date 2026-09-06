# -*- coding: utf-8 -*-
{
    # 🔴 «vehicle dealer» тут не синонім заради краси, а замір. У магазині
    # 06.09.2026: за запитом `car dealership` цей модуль знаходиться, а за
    # `vehicle dealer` видача — ТРИ додатки на весь каталог, і нашого серед них
    # немає. Усі троє мають слово `Vehicle` у назві. Ніша порожня, тож питання
    # не в конкуренції, а в тому, що нас там просто нема кому знайти.
    'name': "3A-dealer — Car Dealership, Vehicle Dealer & Service Workshop",

    'summary': "Car showroom · Auto parts · Service workshop — vehicle dealer management with a document-centric workflow for Odoo",

    'description': """
3A-dealer — a vertical solution for car dealers and service workshops
=====================================================================

Car showroom, auto-parts stock and service workshop in a single module,
with a familiar document-centric workflow.

Key features:

* Document chain: Sale Order, Repair Order, Delivery note / Act / Invoice (each document created "on the basis of" the previous one).
* Workshop repair orders: customer, vehicle (VIN), mileage, mechanics, service advisor, parts & labour, stock control.
* Customer vehicle card file: VIN, brand (logo), repair history, service booking calendar, maintenance reminders.
* Showroom stock: cars as inventory with statuses, trims, colors, options, trade-in.
* Parts & analogs, standard hours, mechanic output.
* Reports in two styles: "Ready reports" (parameter header, Generate, statement) and the interactive Odoo pivot.
* Printable forms (UA): invoice for payment, delivery note, return note, goods-receipt note, power of attorney, reconciliation act.
* Document journals: Date, Number, Customer, Vehicle, Amount, Status.
* Interface in English and Ukrainian.
    """,

    'application': True,
    'post_init_hook': 'post_init_hook',
    'author': "chukhin",
    # Адреса для звернень покупців (видима лише тим, хто завантажив модуль).
    # Її не було взагалі — тобто людині, у якої модуль не встановився, не було
    # куди написати; 17 завантажень і жодного листа саме тому й дивними не були.
    'support': "adealer@yellow.in.ua",
    'website': "https://aktiv.in.ua/dodatky/",
    # Кнопка «Live Preview» на сторінці додатка в Odoo Apps. Це єдиний дозволений
    # спосіб дати зовнішнє посилання: в описі й маніфесті сторонні лінки
    # заборонені правилами стору, а для цього поля воно й передбачене.
    # Вхід demo/demo, дані вигадані й щоніч перестворюються.
    'live_test_url': "https://demo-3adealer.yellow.in.ua",
    'license': "LGPL-3",
    'category': 'Sales',
    'version': '19.0.1.11.2',
    'images': [
        # The first image is the card picture in the App Store listing. A
        # screenshot shrunk to a thumbnail reads as a grey smudge; the banner
        # keeps the name legible. The screenshots stay, as the gallery.
        'static/description/banner.png',
        'static/description/screenshot_1.png',  # Showroom dashboard (EN, USD)
        'static/description/screenshot_2.png',  # Service dashboard (EN)
        'static/description/screenshot_3.png',  # Parts dashboard (EN)
        'static/description/screenshot_4.png',  # Repair order — form (EN)
        'static/description/screenshot_5.png',  # Service calendar (EN)
        'static/description/screenshot_6.png',  # Sales — ready report (EN)
        'static/description/screenshot_7.png',  # ABC analysis report (EN)
        'static/description/screenshot_8.png',  # Customer vehicles (EN)
        'static/description/screenshot_9.png',  # Repair order — journal/list (EN)
    ],

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
        # 🔴 ОДРАЗУ після views.xml, хоч це й файл налаштувань: тут оголошено меню
        # adealer.configuration, а батьком його називають service_booking.xml,
        # error_report_views.xml і organization.xml нижче. На ЧИСТІЙ базі файли
        # читаються по порядку, тож із попереднім місцем (22-м) встановлення падало
        # ParseError «External ID not found: adealer.configuration». Оновлення
        # наявної бази цього не показувало — меню там уже було з минулих версій.
        'views/res_config_settings_views.xml',
        'views/dashboard.xml',  # <-- ПІСЛЯ views.xml: меню «Головна» посилається на menu_root
        'views/templates.xml',
        'views/partner_view.xml',
        'views/vehicles.xml',
        'views/product_template.xml',
        'views/service.xml',
        'views/service_request.xml',  # <-- має бути ПІСЛЯ views.xml: перевизначає меню requests/request_calendar
        'views/service_booking.xml',  # попередній запис + пости + види ремонту
        'data/repair_stage_data.xml',  # стандартні стадії наряду (перед alfa_features)
        'views/alfa_features.xml',  # розширення: нормо-години, стадії, склад авто, кампанії, аналоги
        'views/vehicle_service.xml',  # історія обслуговування + нагадування про ТО
        'views/reports_alfa.xml',  # друковані форми UA: наряд, акт робіт, акт прийому-передачі авто
        'views/reports_ua.xml',  # друковані форми UA: рахунок, видаткова, повернення, прибуткова, довіреність, акт звірки
        'views/sale.xml',
        'views/error_report_views.xml',  # звіти про помилки: список/форма/меню (ПІСЛЯ settings — вживає menu configuration)
        'views/organization.xml',  # generic: Organization dimension on every document
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
            'adealer/static/src/css/theme.css',  # фірмова тема (navy/gold), гейт body.adealer-theme
            'adealer/static/src/css/dashboard.css',
            'adealer/static/src/js/custom.js',
            'adealer/static/src/js/adealer_sidebar.js',
            'adealer/static/src/xml/adealer_sidebar.xml',
            'adealer/static/src/js/dashboard/dashboard.js',
            'adealer/static/src/xml/dashboard.xml',
            'adealer/static/src/css/booking_board.css',
            'adealer/static/src/js/booking_board/board.js',
            'adealer/static/src/xml/booking_board.xml',
        ],
    },
    # Без зовнішніх Python-залежностей: .xlsx читаємо через openpyxl,
    # який входить у стандартні залежності Odoo (працює і на Odoo Online).
}

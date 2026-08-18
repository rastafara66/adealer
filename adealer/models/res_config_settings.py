# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

from .error_report import DEFAULT_URL, PARAM_CONSENT, PARAM_URL

# Home page користувача -> дія (res.users.action_id)
HOME_ACTIONS = {
    'dashboard': 'adealer.action_dashboard',
    'calendar': 'adealer.action_window_repair_calendar',
    'vehicles': 'adealer.action_window_vehicles',
    'repairs': 'adealer.action_window_repair_orders',
    'orders': 'adealer.action_window_sale_orders',
    'products': 'adealer.action_window_products',
    'reports': 'adealer.action_report_ready_sales',
}

# Прапорці показу верхніх розділів меню: поле налаштувань -> xmlid меню.
# Дозволяє відключити будь-який розділ (напр. СТО не потрібен «Showroom»).
# Наші друковані форми — для перемикання формату PDF/HTML глобально
OUR_REPORTS = [
    'adealer.action_report_repair_order', 'adealer.action_report_repair_act',
    'adealer.action_report_car_handover', 'adealer.action_report_invoice_pay',
    'adealer.action_report_vydatkova', 'adealer.action_report_povernennia',
    'adealer.action_report_nadhodzhennia', 'adealer.action_report_dovirenist',
    'adealer.action_report_akt_zvirky',
]

MENU_SECTIONS = {
    'show_menu_vehicles': 'adealer.menu_vehicles',
    'show_menu_showroom': 'adealer.menu_showroom',
    'show_menu_products': 'adealer.menu_products',
    'show_menu_contacts': 'adealer.menu_contacts',
    'show_menu_maintenance': 'adealer.menu_maintenance',
    'show_menu_sales': 'adealer.menu_sales',
    'show_menu_purchases': 'adealer.menu_purchases',
    'show_menu_reports': 'adealer.menu_reports',
}


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    # WareHouses
    wh_id_3a = fields.Char("WH ID 3A", default="WareHouse ID 3A")
    wh_id_1c = fields.Char('WH ID (source)', default="WareHouse ID (source)")    
    wh_name_3a = fields.Char('WH Name 3A', default="WareHouse Name 3A")
    wh_name_1c = fields.Char("WH Name (source)", default="WareHouse Name (source)")
    adealer_sidebar_enabled = fields.Boolean(
        string="Branded theme + side menu (sidebar)",
        help="Enable the 3A-dealer branded theme (navy/gold) and the classic left side "
             "menu. On by default.")
    adealer_brand_logo_default = fields.Boolean(
        string="Brand logo instead of photo",
        help="Show the brand logo as the vehicle image by default")
    adealer_lang = fields.Selection(
        selection='_adealer_lang_selection', string="Interface language",
        help="Interface language for the current user")
    adealer_print_format = fields.Selection([
        ('qweb-pdf', 'PDF (file)'),
        ('qweb-html', 'HTML (in browser)'),
    ], string="Printable form format", default='qweb-pdf',
        help="PDF — a file is downloaded (opens in a PDF viewer). "
             "HTML — the form opens directly in a browser tab (no Adobe/download).")
    adealer_home = fields.Selection([
        ('none', 'Default (last app)'),
        ('dashboard', 'Dashboard (Home)'),
        ('calendar', 'Service calendar (workshop)'),
        ('vehicles', 'Vehicles (showroom)'),
        ('repairs', 'Repair order'),
        ('orders', 'Sale orders'),
        ('products', 'Product list'),
        ('reports', 'Reports — Sales (manager)'),
    ], string="Home page", default='none',
        help="What to open after login for the CURRENT user")
    adealer_autopost_docs = fields.Boolean(
        string="Auto-invoice when the repair order is done",
        help="When a repair order moves to \"Repaired\", automatically create and post "
             "the Act (services) + Delivery note (goods). If off, documents are created "
             "with the \"Create act/delivery note\" buttons.")

    # --- Automatic error reports (opt-in, off by default) ---
    adealer_error_reports = fields.Selection(
        [
            ("on", "Send automatic error reports"),
            ("off", "Do not send anything"),
        ],
        string="3A-dealer error reports",
        config_parameter=PARAM_CONSENT,
        help="Reports carry the error type and the line of code that failed, "
             "never the text of the error, and never anything about your vehicles, "
             "customers or amounts. You can read every queued report before it leaves.")
    adealer_report_url = fields.Char(
        string="3A-dealer reporting endpoint",
        config_parameter=PARAM_URL,
        default=DEFAULT_URL,
        help="Where reports are sent. Point it at your own collector if your "
             "policy forbids outbound calls to third parties.")

    # --- Прапорці показу розділів меню ---
    show_menu_vehicles = fields.Boolean("Vehicles and models")
    show_menu_showroom = fields.Boolean("Showroom")
    show_menu_products = fields.Boolean("Products and services")
    show_menu_contacts = fields.Boolean("Partners and users")
    show_menu_maintenance = fields.Boolean("Maintenance and repair")
    show_menu_sales = fields.Boolean("Sales")
    show_menu_purchases = fields.Boolean("Purchases")
    show_menu_reports = fields.Boolean("Reports")

    def _adealer_lang_selection(self):
        langs = self.env['res.lang'].search([('active', '=', True)])
        return [(l.code, l.name) for l in langs]

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('adealer.wh_id_3a', self.wh_id_3a)
        ICP.set_param('adealer.wh_id_1c', self.wh_id_1c)
        ICP.set_param('adealer.wh_name_3a', self.wh_name_3a)
        ICP.set_param('adealer.wh_name_1c', self.wh_name_1c)
        ICP.set_param('adealer.sidebar_enabled', self.adealer_sidebar_enabled)
        ICP.set_param('adealer.brand_logo_default', self.adealer_brand_logo_default)
        ICP.set_param('adealer.autopost_repair_docs', self.adealer_autopost_docs)
        if self.adealer_lang and self.adealer_lang != self.env.user.lang:
            self.env.user.lang = self.adealer_lang
        if self.adealer_home and self.adealer_home != 'none':
            self.env.user.action_id = self.env.ref(HOME_ACTIONS[self.adealer_home]).id
        else:
            self.env.user.action_id = False
        # показ/приховування розділів меню (глобально) через ir.ui.menu.active
        for fname, xmlid in MENU_SECTIONS.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu:
                menu.sudo().active = bool(self[fname])
        # формат друкованих форм (PDF/HTML) — глобально для наших звітів
        if self.adealer_print_format:
            for xmlid in OUR_REPORTS:
                rep = self.env.ref(xmlid, raise_if_not_found=False)
                if rep and rep.report_type != self.adealer_print_format:
                    rep.sudo().report_type = self.adealer_print_format

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update({
            'wh_id_3a': ICP.get_param('adealer.wh_id_3a'),
            'wh_id_1c': ICP.get_param('adealer.wh_id_1c'),
            'wh_name_3a': ICP.get_param('adealer.wh_name_3a'),
            'wh_name_1c': ICP.get_param('adealer.wh_name_1c'),
            'adealer_sidebar_enabled': ICP.get_param('adealer.sidebar_enabled', 'True') in ('True', 'true', '1', True),
            'adealer_brand_logo_default': ICP.get_param('adealer.brand_logo_default', 'True') in ('True', 'true', '1', True),
            'adealer_lang': self.env.user.lang,
            'adealer_autopost_docs': ICP.get_param('adealer.autopost_repair_docs') in ('True', 'true', '1', True),
        })
        for fname, xmlid in MENU_SECTIONS.items():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            res[fname] = bool(menu.active) if menu else True
        rep0 = self.env.ref('adealer.action_report_repair_order', raise_if_not_found=False)
        res['adealer_print_format'] = rep0.report_type if rep0 else 'qweb-pdf'
        home = 'none'
        uid_action = self.env.user.action_id
        if uid_action:
            for key, xmlid in HOME_ACTIONS.items():
                if self.env.ref(xmlid, raise_if_not_found=False) == uid_action:
                    home = key
                    break
        res['adealer_home'] = home
        # Незадана згода на екрані має читатись як «off»: форма не повинна
        # показувати згоду, якої не давали ([[error_report]] — три стани, не булеве).
        if not res.get('adealer_error_reports'):
            res['adealer_error_reports'] = 'off'
        return res

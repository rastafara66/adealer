# -*- coding: utf-8 -*-
"""Підказки про платні надбудови 3A-dealer.

Безкоштовне ядро — єдине місце, де користувач взагалі може дізнатися, що
частину його роботи вже написано. Без підказки людина роками вважає, що модуль
«не вміє маржу по авто», хоча надбудова існує — а ми вважаємо, що вітрина в
магазині працює сама. Тож ядро показує, що ще є, — рівно там, де цього бракує:
маржу згадуємо на картці авто, огляд DVI — у наряді, крос-номери — на запчастині.

🔴 Два обмеження, без яких це перетворилося б на рекламний спам:

1. Підказка ЗНИКАЄ, щойно надбудову встановлено. Той, хто заплатив, реклами
   свого ж додатка не бачить — інакше це виглядало б знущанням.
2. Підказки вимикаються цілком одним прапорцем у Налаштуваннях
   (`adealer.hide_addon_hints`). Магазинний відгук «нав'язлива реклама» коштує
   дорожче за будь-який клік із підказки.
"""
from markupsafe import Markup, escape

from odoo import api, fields, models

# Ліниві переклади: Odoo 18+ дає фабрику `LazyTranslate(__name__)`, а в Odoo 17
# `_lt` - це сам клас, який модуля не питає. Викликається однаково: `_lt("...")`,
# тож нижче нічого не змінюється.
try:
    from odoo.tools import LazyTranslate

    _lt = LazyTranslate(__name__)
except ImportError:  # Odoo 17 і старіші
    from odoo.tools.translate import _lt

# Параметр вимкнення підказок (Налаштування → 3A-dealer).
PARAM_HIDE = 'adealer.hide_addon_hints'

# Сторінка додатка в магазині. Формат канонічний для apps.odoo.com; усі шість
# сторінок перевірено — віддають 200.
STORE_URL = 'https://apps.odoo.com/apps/modules/19.0/%s/'

# Технічна назва → як подати надбудову. Ціна тут довідкова: у магазині вона та
# сама, що в маніфесті надбудови, і змінюється разом із ним.
ADDONS = {
    'adealer_pro_sales': {
        'title': "3A-dealer Sales Pro",
        'price': "€149",
        'pitch': _lt("Days in stock (aging), reconditioning costs and margin per vehicle, "
                     "reservation deposits, trade-in appraisals, test drives and finance offers."),
    },
    'adealer_pro_service': {
        'title': "3A-dealer Service Pro",
        'price': "€149",
        'pitch': _lt("Digital vehicle inspection (DVI) with a green / yellow / red checklist that "
                     "turns findings into a priced quotation, plus loaner cars, prepaid service "
                     "plans and warranty claims."),
    },
    'adealer_pro_parts': {
        'title': "3A-dealer Parts Pro",
        'price': "€99",
        'pitch': _lt("OEM cross-reference so the counter finds the part by any number it is known "
                     "by, min / max reorder list and barcode lookup."),
    },
    'adealer_autoria': {
        'title': "3A-dealer — AUTO.RIA export",
        'price': "€89",
        'pitch': _lt("Publish your stock to AUTO.RIA as an import feed the cabinet fetches on a "
                     "schedule — no retyping, photos included."),
    },
    'adealer_bank_leasing': {
        'title': "3A-dealer Bank & Leasing",
        'price': "€89",
        'pitch': _lt("Auto-loan / leasing application built from the customer and the car, with an "
                     "indicative monthly payment to quote on the spot and a printable application."),
    },
    'adealer_vin': {
        'title': "3A-dealer VIN decoder",
        'price': "€49",
        'pitch': _lt("Decode the VIN into model year, region and manufacturer, and catch typos by "
                     "the check digit — offline, no key needed."),
    },
}


class AdealerAddonHint(models.AbstractModel):
    """Підмішується в модель, на формі якої є що порадити."""
    _name = 'adealer.addon.hint.mixin'
    _description = 'Paid add-on hint'

    # Html, а не Char: підказка — це список із посиланнями, і рендериться вона
    # один раз тут, а не трьома різними шматками розмітки в трьох формах.
    addon_hint_html = fields.Html(
        'Add-ons', compute='_compute_addon_hint_html', sanitize=False, readonly=True,
        help='What the paid 3A-dealer add-ons would add here. Hidden once the add-on '
             'is installed; can be switched off in Settings.')

    def _addon_hint_names(self):
        """Які надбудови доречні САМЕ на цій моделі (порядок = порядок показу)."""
        return ()

    @api.depends_context('lang')
    def _compute_addon_hint_html(self):
        html = self.env['adealer.addon.hint.mixin']._addon_hint_render(self._addon_hint_names())
        for record in self:
            record.addon_hint_html = html

    @api.model
    def _addon_hint_render(self, names):
        if self.env['ir.config_parameter'].sudo().get_param(PARAM_HIDE):
            return False
        # _installed() кешований (ormcache) — це не запит на кожне відкриття форми.
        installed = self.env['ir.module.module']._installed()
        items = [(name, ADDONS[name]) for name in names
                 if name in ADDONS and name not in installed]
        if not items:
            return False

        rows = Markup().join(
            Markup('<li class="mb-1"><a href="%s" target="_blank" rel="noopener">'
                   '<b>%s</b></a> <span class="text-muted">— %s</span> '
                   '<span class="badge text-bg-light">%s</span></li>') % (
                STORE_URL % name, addon['title'], addon['pitch'], addon['price'])
            for name, addon in items
        )
        title = escape(self.env._("Also available for 3A-dealer"))
        return Markup(
            '<div class="alert alert-light border text-muted small mb-0" role="note">'
            '<i class="fa fa-puzzle-piece me-1"/><b>%s</b>'
            '<ul class="mb-0 mt-1 ps-3">%s</ul>'
            '</div>'
        ) % (title, rows)


# ----------------------------------------------------------------------------
#  Куди підказка чіпляється. Порядок у кортежі — порядок показу на формі:
#  спершу те, що ближче до роботи на цьому екрані.
# ----------------------------------------------------------------------------
class DealerCarAddonHint(models.Model):
    _name = 'dealer.car'
    _inherit = ['dealer.car', 'adealer.addon.hint.mixin']

    def _addon_hint_names(self):
        return ('adealer_pro_sales', 'adealer_vin', 'adealer_autoria', 'adealer_bank_leasing')


class RepairOrderAddonHint(models.Model):
    _name = 'repair.order'
    _inherit = ['repair.order', 'adealer.addon.hint.mixin']

    def _addon_hint_names(self):
        return ('adealer_pro_service',)


class ProductTemplateAddonHint(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'adealer.addon.hint.mixin']

    def _addon_hint_names(self):
        return ('adealer_pro_parts',)

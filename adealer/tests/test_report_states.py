# -*- coding: utf-8 -*-
"""Готові звіти: стан документа — назвою мовою користувача, як у самому документі.

Колонка «Стан» звіту — текст, і Odoo його вже не перекладає: назву беремо з поля моделі в
момент побудови звіту. Власний англійський словник давав українському користувачу «Confirmed» і
«Repaired», а в Odoo 20 ще й називав стан ремонту, якого там уже немає.
"""
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged

LANG = 'uk_UA'


@tagged('post_install', '-at_install')
class TestReportStateLabels(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang(LANG)
        cls.partner = cls.env['res.partner'].create({'name': 'Customer S'})

    def _translate_state(self, model, value, text):
        sel = self.env['ir.model.fields.selection'].search([
            ('field_id.model', '=', model), ('field_id.name', '=', 'state'), ('value', '=', value)])
        self.assertTrue(sel, 'стан %s «%s» є у виборі цієї серії Odoo' % (model, value))
        sel.with_context(lang=LANG).name = text
        # Переклади назв станів Odoo тримає в кеші; у 17–19 і в 20 він скидається по-різному.
        if hasattr(self.env.registry, 'clear_all_caches'):
            self.env.registry.clear_all_caches()
        else:
            self.env.transaction.invalidate_ormcache('stable')

    def _rows(self, report_type):
        today = fields.Date.today()
        wizard = self.env['adealer.report.wizard'].with_context(lang=LANG).create({
            'report_type': report_type, 'partner_id': self.partner.id,
            'date_from': today - timedelta(days=1), 'date_to': today + timedelta(days=1)})
        wizard.action_generate()
        return wizard.line_ids.filtered(lambda line: line.line_type == 'row')

    def test_repair_history_shows_state_in_user_language(self):
        self._translate_state('repair.order', 'draft', 'Новий наряд')
        self.env['repair.order'].create({'partner_id': self.partner.id,
                                         'schedule_date': fields.Datetime.now()})
        self.assertEqual(self._rows('repairs').mapped('state'), ['Новий наряд'])

    def test_customer_orders_show_state_in_user_language(self):
        self._translate_state('sale.order', 'draft', 'Пропозиція')
        self.env['sale.order'].create({'partner_id': self.partner.id})
        self.assertEqual(self._rows('orders').mapped('state'), ['Пропозиція'])

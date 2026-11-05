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
        # Запис назви сам перебудовує моделі й скидає кеш перекладів (18, 19 і 20).
        sel.with_context(lang=LANG).name = text

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


@tagged('post_install', '-at_install')
class TestReportPeriodWholeDays(TransactionCase):
    """Період звіту — цілі дні за часом користувача, і останній день теж, однаково в усіх серіях.

    Дата й час документа лежать у базі в UTC. Odoo 19 і 20 переводять дату в умові на пояс користувача
    самі, Odoo 18 — ні: там документ о 00:30 за Києвом потрапляв у сусідній день.
    """

    TZ = 'Europe/Kyiv'          # 31.10.2026 — UTC+2 (літній час скінчився 25.10)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = cls.TZ
        cls.partner = cls.env['res.partner'].create({'name': 'Customer P'})

    def _report(self, report_type):
        day = fields.Date.to_date('2026-10-31')
        wizard = self.env['adealer.report.wizard'].with_context(tz=self.TZ).create({
            'report_type': report_type, 'partner_id': self.partner.id, 'date_from': day, 'date_to': day})
        wizard.action_generate()
        return wizard.line_ids.filtered(lambda line: line.line_type == 'row').mapped('name')

    def test_repair_history_takes_the_whole_last_day(self):
        RO = self.env['repair.order']
        names = {}
        for label, utc in (('00:30 31.10', '2026-10-30 22:30:00'), ('12:00 31.10', '2026-10-31 10:00:00'),
                           ('23:30 31.10', '2026-10-31 21:30:00'), ('00:30 01.11', '2026-10-31 22:30:00')):
            names[label] = RO.create({'partner_id': self.partner.id,
                                      'schedule_date': fields.Datetime.to_datetime(utc)}).name
        self.assertEqual(sorted(self._report('repairs')),
                         sorted(names[k] for k in ('00:30 31.10', '12:00 31.10', '23:30 31.10')))

    def test_customer_orders_take_the_whole_last_day(self):
        SO = self.env['sale.order']
        inside = SO.create({'partner_id': self.partner.id,
                            'date_order': fields.Datetime.to_datetime('2026-10-31 15:00:00')})
        SO.create({'partner_id': self.partner.id,
                   'date_order': fields.Datetime.to_datetime('2026-10-31 22:30:00')})     # 01.11 за Києвом
        self.assertEqual(self._report('orders'), [inside.name])

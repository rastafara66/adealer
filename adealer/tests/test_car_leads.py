# -*- coding: utf-8 -*-
"""Заявка CRM ↔ авто зі складу (1.20.0) і вигляд картки авто.

Заявки з майданчиків лягатимуть у CRM з прив'язкою до авто, тож тут — те, що
треба надбудовам вивантаження: поле на заявці, лічильник і кнопка на картці.
І дві речі, яких тести моделі не бачать, бо вони у вигляді: рік моделі без
роздільника тисяч («2,023») і поля VIN-декодера одразу після року.
"""
from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestCarLeads(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.car = cls.env['dealer.car'].create({'vin': 'TSTLD000000000001'})

    def test_lead_counted_on_car(self):
        self.assertEqual(self.car.lead_count, 0)
        self.env['crm.lead'].create({'name': 'Test lead', 'dealer_car_id': self.car.id})
        self.env['crm.lead'].create({'name': 'Test lead 2', 'dealer_car_id': self.car.id})
        self.car.invalidate_recordset(['lead_ids', 'lead_count'])
        self.assertEqual(self.car.lead_count, 2)

    def test_leads_button_opens_and_prefills(self):
        action = self.car.action_view_leads()
        self.assertEqual(action['res_model'], 'crm.lead')
        self.assertEqual(action['domain'], [('dealer_car_id', '=', self.car.id)])
        lead = self.env['crm.lead'].with_context(action['context']).create({'name': 'From the card'})
        self.assertEqual(lead.dealer_car_id, self.car,
                         "заявка з кнопки на картці одразу прив'язана до авто")

    def test_deleting_car_keeps_lead(self):
        lead = self.env['crm.lead'].create({'name': 'Keep me', 'dealer_car_id': self.car.id})
        self.car.unlink()
        self.assertTrue(lead.exists())
        self.assertFalse(lead.dealer_car_id)

    def test_vehicle_on_lead_form(self):
        arch = etree.fromstring(self.env['crm.lead'].get_view(view_type='form')['arch'])
        self.assertTrue(arch.xpath("//field[@name='dealer_car_id']"),
                        "поле «Vehicle» є на формі заявки")

    def test_model_year_without_thousands_separator(self):
        # Odoo 18–20: опція віджета цілого числа — enable_formatting; «format»
        # він мовчки ігнорує. У списку опція діє лише з явним widget.
        for view_type in ('form', 'list'):
            arch = etree.fromstring(self.env['dealer.car'].get_view(view_type=view_type)['arch'])
            nodes = arch.xpath("//field[@name='model_year']")
            self.assertTrue(nodes, view_type)
            for node in nodes:
                self.assertIn("'enable_formatting': false", node.get('options') or '', view_type)
                if view_type == 'list':
                    self.assertEqual(node.get('widget'), 'integer')

    def test_model_year_last_in_vehicle_group(self):
        # Після року надбудова VIN-декодера ставить свої поля; стан, перша
        # реєстрація, пробіг і trade-in мають іти перед ним.
        arch = etree.fromstring(self.env['dealer.car'].get_view(view_type='form')['arch'])
        group = arch.xpath("//field[@name='model_year']/..")[0]
        names = [n.get('name') for n in group.iter('field')]
        for name in ('condition', 'first_registration', 'mileage_km', 'is_trade_in'):
            self.assertLess(names.index(name), names.index('model_year'), name)

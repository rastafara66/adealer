# -*- coding: utf-8 -*-
"""Попередній запис: те, що менеджер бачить у календарі й на дошці по постах.

Підпис запису — «держномер модель · клієнт · роботи», як клітинка розкладу в
обліковій системі, з якої переходять; клієнт «зі слів» (без картки контакту)
не губиться; колір виду ремонту доходить до запису.
"""
from datetime import datetime

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestServiceBooking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Booking = cls.env['adealer.service.booking']
        brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'Brand T'})
        cls.model = cls.env['fleet.vehicle.model'].create({'name': 'Model T', 'brand_id': brand.id})
        cls.partner = cls.env['res.partner'].create({'name': 'Customer T'})
        cls.kind = cls.env['adealer.repair.type'].create({'name': 'Kind T',
                                                          'html_color': '#fce4b8'})

    def _book(self, **vals):
        vals.setdefault('appointment_datetime', datetime(2026, 9, 14, 8, 0))
        return self.Booking.create(vals)

    def test_label_reads_like_the_schedule(self):
        booking = self._book(plate='AA1234BB', model_id=self.model.id,
                             partner_id=self.partner.id, requested_works='Oil change')
        self.assertEqual(booking.display_name, 'AA1234BB Model T · Customer T · Oil change')

    def test_customer_without_contact_is_kept(self):
        """Ім'я «зі слів» стоїть там, де стояв би контакт, — і нікуди не зникає."""
        booking = self._book(plate='AA1234BB', customer_name='Olexandr')
        self.assertFalse(booking.partner_id)
        self.assertEqual(booking.display_name, 'AA1234BB · Olexandr')

    def test_contact_wins_over_the_name_given(self):
        booking = self._book(partner_id=self.partner.id, customer_name='Olexandr')
        self.assertEqual(booking.display_name, 'Customer T')

    def test_number_only_when_nothing_else(self):
        booking = self._book()
        self.assertTrue(booking.name.strip('/'), 'номер запису видається послідовністю')
        self.assertEqual(booking.display_name, booking.name)

    def test_long_works_are_cut(self):
        booking = self._book(plate='AA1234BB', requested_works='x' * 40)
        self.assertEqual(booking.display_name, 'AA1234BB · ' + 'x' * 30 + '…')

    def test_repair_type_color_reaches_the_booking(self):
        booking = self._book(repair_type_id=self.kind.id)
        self.assertEqual(booking.repair_type_color, '#fce4b8')
        self.kind.html_color = False
        self.assertFalse(booking.repair_type_color)

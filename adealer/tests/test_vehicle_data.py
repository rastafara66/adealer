# -*- coding: utf-8 -*-
"""Дані авто для оголошень: стан, потужність, дані фургона.

Поля живуть у ядрі, бо їх читають усі надбудови вивантаження на майданчики.
Тут — поведінка, якої не видно з форми: стан trade-in, перерахунок к.с. ↔ кВт.
"""
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestVehicleData(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Car = cls.env['dealer.car']

    def test_new_car_is_new(self):
        car = self.Car.create({'vin': 'TSTVD000000000001'})
        self.assertEqual(car.condition, 'new')

    def test_trade_in_is_used(self):
        car = self.Car.create({'vin': 'TSTVD000000000002', 'is_trade_in': True})
        self.assertEqual(car.condition, 'used')

    def test_marking_trade_in_later_makes_it_used(self):
        car = self.Car.create({'vin': 'TSTVD000000000003'})
        car.is_trade_in = True
        self.assertEqual(car.condition, 'used')

    def test_manual_used_is_kept(self):
        # Вживане, куплене не в обмін: людина обрала стан сама, перерахунок
        # його не скидає ні при створенні, ні коли знімають позначку trade-in.
        car = self.Car.create({'vin': 'TSTVD000000000004', 'condition': 'used'})
        self.assertEqual(car.condition, 'used')
        car.write({'is_trade_in': True})
        car.write({'is_trade_in': False})
        self.assertEqual(car.condition, 'used')

    def test_power_hp_follows_kw(self):
        car = self.Car.create({'vin': 'TSTVD000000000005', 'power_kw': 110})
        self.assertEqual(car.power_hp, 150)

    def test_power_kw_follows_hp(self):
        car = self.Car.create({'vin': 'TSTVD000000000006'})
        car.power_hp = 136
        self.assertEqual(car.power_kw, 100)
        self.assertEqual(car.power_hp, 136, "к.с. → кВт → к.с. дає те саме число")

    def test_van_data_is_kept(self):
        car = self.Car.create({
            'vin': 'TSTVD000000000007',
            'gross_weight_kg': 3500, 'payload_kg': 1200, 'axles': 2,
            'cargo_length_mm': 3450, 'cargo_width_mm': 1780, 'cargo_height_mm': 1900,
            'cargo_volume_m3': 11.5, 'euro_pallets': 4,
            'sliding_door': 'both', 'tail_lift': True,
        })
        self.assertEqual((car.payload_kg, car.euro_pallets, car.sliding_door),
                         (1200, 4, 'both'))
        self.assertAlmostEqual(car.cargo_volume_m3, 11.5)

    def test_body_drive_doors_are_kept(self):
        # Кузов, привід і двері — для оголошень на майданчиках (AUTO.RIA без кузова не приймає).
        car = self.Car.create({'vin': 'TSTVD000000000008', 'body_type': 'van',
                               'drive_type': 'fwd', 'doors': 4})
        self.assertEqual((car.body_type, car.drive_type, car.doors), ('van', 'fwd', 4))

# -*- coding: utf-8 -*-
"""Сканер штрихкодів у документах: товар — рядком одним скануванням.

Власник, 07.10.2026: «сканування в 3адилер і актив — найперше». Запчастини
продаються за кодами; скан мусить додати товар рядком, а повторний скан того
самого товару — збільшити кількість, а не плодити рядки.
"""
from lxml import etree

from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBarcodeScan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, lang="en_US"))
        cls.partner = cls.env["res.partner"].create({"name": "Scan customer"})
        Product = cls.env["product.product"]
        cls.filter = Product.create({
            "name": "Oil filter", "barcode": "4820000000017", "default_code": "OF-17",
            "type": "consu", "list_price": 120.0, "standard_price": 80.0})
        cls.labour = Product.create({
            "name": "Diagnostics", "barcode": "2000000000015", "type": "service",
            "list_price": 500.0})
        cls.not_for_sale = Product.create({
            "name": "Internal tool", "barcode": "2000000000022", "type": "consu",
            "sale_ok": False})

    def _scan(self, form, code):
        form["_barcode_scanned"] = code

    # --- продаж ---------------------------------------------------------------

    def test_scan_adds_a_line_and_a_second_scan_raises_the_quantity(self):
        with Form(self.env["sale.order"]) as order:
            order.partner_id = self.partner
            self._scan(order, "4820000000017")
            self._scan(order, "4820000000017")
        sale = order.record
        self.assertEqual(len(sale.order_line), 1, "повторний скан мав збільшити кількість, а не додати рядок")
        self.assertEqual(sale.order_line.product_id, self.filter)
        self.assertEqual(sale.order_line.product_uom_qty, 2.0)
        self.assertEqual(sale.order_line.price_unit, 120.0, "ціна рядка мала підставитись, як при ручному виборі")

    def test_internal_reference_works_when_there_is_no_such_barcode(self):
        with Form(self.env["sale.order"]) as order:
            order.partner_id = self.partner
            self._scan(order, "OF-17")
        self.assertEqual(order.record.order_line.product_id, self.filter)

    def test_unknown_code_adds_nothing_and_explains(self):
        sale = self.env["sale.order"].create({"partner_id": self.partner.id})
        result = sale.on_barcode_scanned("0000000000000")
        self.assertIn("warning", result or {}, "невідомий код мусить пояснити, що сталось")
        self.assertIn("What to do", result["warning"]["message"])
        self.assertFalse(sale.order_line)

    def test_confirmed_order_is_not_changed(self):
        sale = self.env["sale.order"].create({"partner_id": self.partner.id})
        sale.on_barcode_scanned("4820000000017")
        sale.action_confirm()
        result = sale.on_barcode_scanned("4820000000017")
        self.assertIn("warning", result or {})
        self.assertEqual(sale.order_line.product_uom_qty, 1.0, "проведене замовлення змінилось від скану")

    def test_product_not_for_sale_is_refused(self):
        sale = self.env["sale.order"].create({"partner_id": self.partner.id})
        result = sale.on_barcode_scanned("2000000000022")
        self.assertIn("warning", result or {})
        self.assertFalse(sale.order_line)

    # --- закупівля ------------------------------------------------------------

    def test_purchase_order_line_and_quantity(self):
        with Form(self.env["purchase.order"]) as order:
            order.partner_id = self.partner
            self._scan(order, "4820000000017")
            self._scan(order, "4820000000017")
        purchase = order.record
        self.assertEqual(len(purchase.order_line), 1)
        self.assertEqual(purchase.order_line.product_qty, 2.0)

    # --- заказ-наряд ----------------------------------------------------------

    def test_repair_order_part_goes_to_parts_and_gets_a_price(self):
        repair = self.env["repair.order"].create({"partner_id": self.partner.id})
        repair.on_barcode_scanned("4820000000017")
        repair.on_barcode_scanned("2000000000015")
        self.assertEqual(repair.part_line_ids.product_id, self.filter)
        self.assertEqual(repair.part_line_ids.price_unit, 120.0,
                         "ціна рядка наряду ставиться onchange рядка — його мало бути викликано")
        self.assertEqual(repair.service_line_ids.product_id, self.labour,
                         "роботу мало покласти у вкладку робіт, де її видно")

    def test_repair_order_form_scan(self):
        repair = self.env["repair.order"].create({"partner_id": self.partner.id})
        with Form(repair) as form:
            self._scan(form, "4820000000017")
            self._scan(form, "4820000000017")
        self.assertEqual(len(repair.part_line_ids), 1)
        self.assertEqual(repair.part_line_ids.product_uom_qty, 2.0)

    # --- поряд із «Активом» -----------------------------------------------------

    def test_the_scanner_widget_is_in_the_form_once_even_if_added_twice(self):
        """Другий модуль (у «Активі» такий самий сканер) додає віджет у ту ж
        форму вдруге. Два віджети = два onchange на один скан = два рядки."""
        self.env["ir.ui.view"].create({
            "name": "second scanner widget",
            "model": "sale.order",
            "inherit_id": self.env.ref("sale.view_order_form").id,
            "arch": '<xpath expr="//sheet" position="inside">'
                    '<field name="_barcode_scanned" widget="barcode_handler"/></xpath>',
        })
        arch = self.env["sale.order"].get_views([(False, "form")])["views"]["form"]["arch"]
        nodes = etree.fromstring(arch).xpath("//field[@name='_barcode_scanned']")
        self.assertEqual(len(nodes), 1)

# -*- coding: utf-8 -*-
"""Product groups: icons picked from names, and the product list as a tree of groups.

The icon rules are ordered, and two neighbouring rules often claim the same
name ("oil filter" is a filter and an oil). Each pair below pins one such
dispute, so reordering ICON_RULES shows up here instead of silently changing
the icons of dozens of groups.
"""
from lxml import etree

from odoo.tests import TransactionCase, tagged

from odoo.addons.adealer.models.product_category import icon_for_name


@tagged('post_install', '-at_install')
class TestProductCategoryIcon(TransactionCase):

    def test_narrow_rule_wins(self):
        cases = {
            'Фільтр масляний': 'fa-filter',          # filter, not oil
            'Масло КПП': 'fa-tint',                  # oil, not transmission
            'Масло кондиціонер': 'fa-tint',          # oil, not air conditioning
            'Мойка автомобиля': 'fa-shower',         # wash, not vehicle
            'Покраска автомобиля': 'fa-paint-brush',  # paint, not vehicle
            'Осмотр ходовой': 'fa-stethoscope',      # inspection, not chassis
            'Система охлаждения ДВС': 'fa-thermometer-half',  # cooling, not engine
            'Запчасти НЕ оригинал': 'fa-puzzle-piece',  # aftermarket, not genuine
            'Запчасти ОРИГИНАЛ': 'fa-certificate',
            'Аксессуары оригинал': 'fa-shopping-bag',  # accessories, not genuine
            'Неліквідні товари': 'fa-ban',           # obsolete, not goods
            'Хозтовары': 'fa-home',                  # household, not goods
            'Мебель МБП': 'fa-bed',                  # furniture, not low-value assets
            'Строительные материалы': 'fa-building',  # construction, not materials
            'Материалы СТО': 'fa-cube',              # materials, not workshop works
            'Подготовка MIX': 'fa-paint-brush',      # paint mix, not preparation
            'Розыгрыш авто': 'fa-trophy',            # prize, not vehicle
            'Знаки ПБ': 'fa-fire-extinguisher',      # fire safety, not signs
        }
        for name, icon in cases.items():
            with self.subTest(name=name):
                self.assertEqual(icon_for_name(name), icon)

    def test_latin_lookalikes_and_spaces(self):
        # Latin "i" inside a Cyrillic word, and a double space between words.
        self.assertEqual(icon_for_name('Аксесуари оригiнал Бутiк'), 'fa-shopping-bag')
        self.assertEqual(icon_for_name('Запчасти  НЕ оригинал'), 'fa-puzzle-piece')
        self.assertEqual(icon_for_name('ОС c 2016'), 'fa-briefcase')

    def test_vehicle_model_and_brand(self):
        self.assertEqual(icon_for_name('MODEL-X 1.6 бензин'), 'fa-car')
        self.assertEqual(icon_for_name('MODEL-X 2.0 2010 -'), 'fa-car')
        self.assertEqual(icon_for_name('Zetamobile', brands={'zetamobile'}), 'fa-car')
        self.assertEqual(icon_for_name('Zetamobile'), '')

    def test_icon_on_create_and_inherited(self):
        Category = self.env['product.category']
        parent = Category.create({'name': 'Ходова частина'})
        child = Category.create({'name': 'Задня частина', 'parent_id': parent.id})
        self.assertEqual(parent.adealer_icon, 'fa-road')
        self.assertEqual(child.adealer_icon, 'fa-road', "a name that says nothing takes the parent's icon")
        lonely = Category.create({'name': 'Qwerty'})
        self.assertFalse(lonely.adealer_icon, "no match and no parent: the list shows a folder")

    def test_brand_from_fleet(self):
        self.env['fleet.vehicle.model.brand'].create({'name': 'Zetamobile'})
        category = self.env['product.category'].create({'name': 'Zetamobile'})
        self.assertEqual(category.adealer_icon, 'fa-car')

    def test_manual_icon_kept_and_cleared_icon_repicked(self):
        category = self.env['product.category'].create({'name': 'Шини', 'adealer_icon': 'fa-star'})
        self.assertEqual(category.adealer_icon, 'fa-star', "an icon given on create is kept")
        category.name = 'Масла'
        self.assertEqual(category.adealer_icon, 'fa-star', "renaming does not overwrite a chosen icon")
        category.adealer_icon = False
        self.assertEqual(category.adealer_icon, 'fa-tint', "clearing the icon picks it from the name again")
        category.action_adealer_pick_icons()
        self.assertEqual(category.adealer_icon, 'fa-tint')


@tagged('post_install', '-at_install')
class TestProductListByGroup(TransactionCase):

    def test_products_open_as_list_first(self):
        for xmlid in ('adealer.action_window_products', 'adealer.action_window_products_by_group'):
            action = self.env.ref(xmlid)
            with self.subTest(action=xmlid):
                self.assertEqual(action.view_mode.split(',')[0], 'list')
                first = action.view_ids.sorted('sequence')[:1]
                self.assertEqual(first.view_mode, 'list')
                self.assertEqual(first.view_id, self.env.ref('adealer.view_product_list_groups'))

    def test_by_group_action_groups_by_category(self):
        action = self.env.ref('adealer.action_window_products_by_group')
        self.assertIn("'search_default_group_by_categ_id': 1", action.context)
        search = self.env['product.product'].get_views([(False, 'search')])['views']['search']['arch']
        self.assertTrue(etree.fromstring(search).xpath("//filter[@name='group_by_categ_id']"),
                        "the search view must keep the filter the action turns on")

    def test_tree_list_gets_every_group(self):
        # Without groups_limit Odoo sends the first 80 groups and the tree
        # silently loses branches.
        arch = etree.fromstring(self.env.ref('adealer.view_product_list_groups').arch)
        self.assertEqual(arch.get('js_class'), 'adealer_category_tree_list')
        self.assertGreaterEqual(int(arch.get('groups_limit')), 1000)

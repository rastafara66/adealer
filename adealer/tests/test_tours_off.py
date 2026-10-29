# -*- coding: utf-8 -*-
"""Навчальні тури Odoo («краплі») вимкнено назавжди.

Правило власника 29.10.2026: «в усіх базах … НАЗАВЖДИ». Перекрити обчислення
було замало: поле збережене, тож адмін, створений разом із базою ДО
встановлення 3A-dealer, лишався з турами; а ручний старт тура вмикав їх знову
через `switch_tour_enabled(True)`.
"""
from unittest.mock import patch

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestToursOff(TransactionCase):

    def _admin(self, login):
        Users = self.env['res.users']
        groups = 'groups_id' if 'groups_id' in Users._fields else 'groups_id'
        return Users.create({
            'name': login, 'login': login,
            groups: [Command.set([self.env.ref('base.group_system').id])],
        })

    def test_new_admin_has_no_tours(self):
        admin = self._admin('adealer_tours_new_admin')
        self.assertTrue(admin._is_admin())
        # web_tour вмикає тури адміну бази без демо-модулів і поза тестами —
        # відтворюємо саме ці умови, інакше перевірка зеленіла б і без нас.
        Module = type(self.env['ir.module.module'])
        with patch('odoo.modules.module.current_test', None, create=True), \
                patch.object(Module, 'search_count', return_value=0):
            admin._compute_tour_enabled()
        self.assertFalse(admin.tour_enabled)

    def test_manual_tour_does_not_switch_tours_on(self):
        admin = self._admin('adealer_tours_switch')
        result = self.env['res.users'].with_user(admin).switch_tour_enabled(True)
        self.assertFalse(result)
        self.assertFalse(admin.tour_enabled)

    def test_existing_users_switched_off(self):
        admin = self._admin('adealer_tours_existing')
        # Як у базі, де користувач був до встановлення 3A-dealer.
        admin.write({'tour_enabled': True})
        self.assertTrue(admin.tour_enabled)
        self.env['res.users']._adealer_tours_off()
        self.assertFalse(admin.tour_enabled)

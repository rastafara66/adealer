# -*- coding: utf-8 -*-
"""Після входу менеджер потрапляє на Головну 3A-dealer.

Правило власника 15.09.2026. Перевіряємо саме рішення, яке віддається
клієнту в `session_info`, а не лише наявність пункту меню: меню було й раніше,
а людина все одно опинялась у першому застосунку сітки.
"""
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestHomeAction(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env.ref('adealer.action_dashboard')
        cls.Http = cls.env['ir.http']

    def _user(self, login, groups):
        return self.env['res.users'].create({
            'name': login, 'login': login,
            'group_ids': [Command.set([self.env.ref(g).id for g in groups])],
        })

    def test_manager_lands_on_the_dashboard(self):
        manager = self._user('adealer_home_manager', ['base.group_user'])
        # Рівень «Користувач» кожен співробітник отримує автоматично.
        self.assertTrue(manager.has_group('adealer.group_adealer_user'))
        self.assertEqual(self.Http._adealer_home_action_id(manager), self.dashboard.id)

    def test_explicit_choice_wins(self):
        manager = self._user('adealer_home_choice', ['base.group_user'])
        calendar = self.env.ref('adealer.action_window_repair_calendar')
        manager.action_id = calendar.id
        self.assertFalse(self.Http._adealer_home_action_id(manager),
                         "явний вибір людини не можна перебивати")

    def test_portal_user_gets_nothing(self):
        portal = self._user('adealer_home_portal', ['base.group_portal'])
        self.assertFalse(self.Http._adealer_home_action_id(portal))

    def test_setting_automatic_clears_personal_choice(self):
        """«Автоматично за роллю» у Налаштуваннях знімає особистий вибір."""
        self.env.user.action_id = self.env.ref('adealer.action_window_vehicles').id
        settings = self.env['res.config.settings'].create({'adealer_home': 'none'})
        settings.execute()
        self.assertFalse(self.env.user.action_id)

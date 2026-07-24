# -*- coding: utf-8 -*-
"""Зробити дашборд «Головна» стартовою сторінкою для наявних користувачів
(тих, хто ще не обрав власну home-дію). Виконується при оновленні до 19.0.1.4.0."""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref('adealer.action_dashboard', raise_if_not_found=False)
    if not action:
        return
    users = env['res.users'].search([('share', '=', False), ('action_id', '=', False)])
    if users:
        users.write({'action_id': action.id})

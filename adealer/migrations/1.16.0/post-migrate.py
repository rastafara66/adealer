# -*- coding: utf-8 -*-
"""Product groups get an icon picked from their name.

The icon is chosen when a group is created. Groups that existed before
19.0.1.16.0 were created without one, so they get it here, once; a group
whose icon someone already set is left alone.
"""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['product.category'].search([('adealer_icon', '=', False)])._adealer_pick_icon()

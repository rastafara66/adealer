# -*- coding: utf-8 -*-
"""Заявка CRM знає авто, про яке питає покупець (з 1.20.0).

Заявки з майданчиків (mobile.de, AUTO.RIA) і ті, що менеджер заводить руками,
прив'язуються до картки авто зі складу: з заявки видно машину, а на картці —
скільки людей питали саме її. Поле в ядрі, бо заявки кладуть різні надбудови
вивантаження, і жодна не має залежати від іншої."""
from odoo import fields, models


class CrmLeadVehicle(models.Model):
    _inherit = 'crm.lead'

    dealer_car_id = fields.Many2one(
        'dealer.car', 'Vehicle', index=True, tracking=True, ondelete='set null',
        help='The vehicle from the showroom stock the customer is asking about. '
             'Leads from car portals are linked to their vehicle automatically; '
             'the vehicle card shows all leads about it.')

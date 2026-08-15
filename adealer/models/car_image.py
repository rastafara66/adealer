# -*- coding: utf-8 -*-
"""Extra photos of a showroom vehicle. The car keeps one main photo directly;
these are the rest of the gallery — the shots a listing or a showroom card needs.
"""
from odoo import models, fields


class DealerCarImage(models.Model):
    _name = 'dealer.car.image'
    _description = 'Vehicle photo'
    _inherit = ['image.mixin']
    _order = 'sequence, id'

    car_id = fields.Many2one('dealer.car', 'Vehicle', required=True,
                             ondelete='cascade', index=True)
    name = fields.Char('Title')
    sequence = fields.Integer(default=10)

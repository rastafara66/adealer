
# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    #VHS_id = fields.Many2one('fleet.vehicle', string='VHS')
    base_service = fields.Boolean(default=False, string='Base service')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.name = self.vehicle_id.name

    @api.onchange('base_service')
    def _onchange_base_service(self):
        if self.base_service:
            self.type = 'service'
            self.sale_ok = False
            self.purchase_ok = False
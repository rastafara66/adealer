from odoo import models, fields, api

class MaintenanceRequest(models.Model):
    
    _inherit = 'maintenance.request'
    _name = 'maintenance.request'
    _description = 'Maintenance Request'

    repair_order = fields.Many2one('repair.order', string='Repair Order')#, required=True
    master_id = fields.Many2one('res.users', string='Master')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    partner_id = fields.Many2one('res.partner', string='Partner')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id_(self):
        if self.vehicle_id:
                self.partner_id = self.vehicle_id.partner_id
from odoo import models, fields, api

class MaintenanceRequest(models.Model):
    
    _inherit = 'maintenance.request'
    _name = 'maintenance.request'
    _description = 'Maintenance Request'

    repair_order = fields.Many2one('repair.order', string='Repair Order',
                                   help='The repair order linked to this maintenance request.')#, required=True
    master_id = fields.Many2one('res.users', string='Master',
                                help='Who is in charge of the request.')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle',
                                 help='The vehicle the request is about.')
    partner_id = fields.Many2one('res.partner', string='Partner',
                                 help='The customer the request is for.')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id_(self):
        if self.vehicle_id:
                self.partner_id = self.vehicle_id.partner_id
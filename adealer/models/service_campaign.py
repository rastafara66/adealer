# -*- coding: utf-8 -*-
"""Сервісні/гарантійні кампанії, відкликання (аналог 1С «Альфа-Авто»:
Справочник.СервисныеКампании + РегистрСведений.ВыполнениеСервисныхКампаний +
Обработка.ЗагрузкаДанныхСервиснойКампании).

Виробник оголошує кампанію (напр. відкликання для заміни вузла), що
стосується переліку VIN. По кожному авто ведеться статус виконання
(очікує / виконано), з посиланням на наряд, яким кампанію закрито.
"""
from odoo import models, fields, api, _


class ServiceCampaign(models.Model):
    _name = 'dealer.service.campaign'
    _description = 'Service campaign'
    _inherit = ['mail.thread']
    _order = 'date_start desc, id desc'

    name = fields.Char('Campaign name', required=True, tracking=True)
    code = fields.Char('Code/number', copy=False, index=True)
    campaign_type = fields.Selection([
        ('recall', 'Recall'),
        ('warranty', 'Warranty'),
        ('service', 'Service action'),
    ], 'Type', default='recall', required=True, tracking=True)
    date_start = fields.Date('Start date', default=fields.Date.context_today)
    date_end = fields.Date('End date')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], 'State', default='draft', required=True, tracking=True)
    description = fields.Html('Description / instructions')
    service_product_id = fields.Many2one('product.product', 'Campaign work',
                                         domain="[('type', '=', 'service')]",
                                         help='Service performed within the campaign')
    line_ids = fields.One2many('dealer.service.campaign.line', 'campaign_id', 'Vehicles')
    vehicle_count = fields.Integer('Total vehicles', compute='_compute_counts', store=True)
    done_count = fields.Integer('Done', compute='_compute_counts', store=True)
    progress = fields.Float('Progress, %', compute='_compute_counts', store=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.depends('line_ids.state')
    def _compute_counts(self):
        for camp in self:
            total = len(camp.line_ids)
            done = len(camp.line_ids.filtered(lambda l: l.state == 'done'))
            camp.vehicle_count = total
            camp.done_count = done
            camp.progress = (done / total * 100.0) if total else 0.0

    def action_activate(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_add_all_of_model(self):
        """Додати всі авто вибраної моделі (швидке наповнення кампанії)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add vehicles'),
            'res_model': 'fleet.vehicle',
            'view_mode': 'tree',
            'target': 'new',
        }


class ServiceCampaignLine(models.Model):
    _name = 'dealer.service.campaign.line'
    _description = 'Vehicle in a service campaign'
    _order = 'state, id'

    campaign_id = fields.Many2one('dealer.service.campaign', 'Campaign', required=True,
                                  ondelete='cascade', index=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', index=True)
    vin = fields.Char('VIN', help='VIN, if the vehicle is not yet in the database')
    partner_id = fields.Many2one('res.partner', 'Owner')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('notified', 'Notified'),
        ('done', 'Done'),
        ('rejected', 'Customer refusal'),
    ], 'Status', default='pending', required=True, index=True)
    repair_order_id = fields.Many2one('repair.order', 'Order', copy=False,
                                      help='The order that closed the vehicle campaign')
    done_date = fields.Date('Completion date')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.vin = self.vehicle_id.vin_sn
            self.partner_id = self.vehicle_id.partner_id

    def action_mark_done(self):
        self.write({'state': 'done', 'done_date': fields.Date.context_today(self)})


class RepairOrderCampaign(models.Model):
    """Підказка на наряді: чи підпадає авто під активні кампанії."""
    _inherit = 'repair.order'

    active_campaign_ids = fields.Many2many('dealer.service.campaign',
                                           compute='_compute_active_campaigns',
                                           string='Active campaigns for the vehicle')
    active_campaign_count = fields.Integer(compute='_compute_active_campaigns')

    @api.depends('vehicle_id')
    def _compute_active_campaigns(self):
        Line = self.env['dealer.service.campaign.line']
        for order in self:
            camps = self.env['dealer.service.campaign']
            if order.vehicle_id:
                lines = Line.search([
                    ('vehicle_id', '=', order.vehicle_id.id),
                    ('state', 'in', ('pending', 'notified')),
                    ('campaign_id.state', '=', 'active'),
                ])
                camps = lines.mapped('campaign_id')
            order.active_campaign_ids = camps
            order.active_campaign_count = len(camps)

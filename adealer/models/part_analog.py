# -*- coding: utf-8 -*-
"""Analogs (крос-номери) запчастин and облік упущеного попиту
(аналог 1С «Альфа-Авто»: РегистрСведений.ГруппыАналогов +
Обработка.ПодборНоменклатуры + Обработка/Отчет.УпущенныйСпрос).

Analog group об'єднує взаємозамінні деталі (оригінал + замінники різних
виробників). Із будь-якої деталі видно її аналоги і залишки to кожному —
щоб підібрати наявний замінник.
"""
from odoo import models, fields, api


class PartAnalogGroup(models.Model):
    _name = 'adealer.part.analog.group'
    _description = 'Parts analog group'
    _order = 'name'

    name = fields.Char('Group name', required=True,
                       help='e.g. "Oil filter (engine 1.6)"')
    note = fields.Text('Description')
    product_ids = fields.One2many('product.template', 'analog_group_id', 'Analogs')
    product_count = fields.Integer('Analogs count', compute='_compute_product_count')
    active = fields.Boolean(default=True)

    @api.depends('product_ids')
    def _compute_product_count(self):
        for group in self:
            group.product_count = len(group.product_ids)


class ProductTemplateAnalog(models.Model):
    _inherit = 'product.template'

    analog_group_id = fields.Many2one('adealer.part.analog.group', 'Analog group',
                                      index=True,
                                      help='Interchangeable parts within one group')
    analog_ids = fields.Many2many('product.template', string='Analogs (replacements)',
                                  compute='_compute_analog_ids',
                                  help='Other parts from the same analog group')
    analog_count = fields.Integer('Analogs', compute='_compute_analog_ids')

    @api.depends('analog_group_id', 'analog_group_id.product_ids')
    def _compute_analog_ids(self):
        for product in self:
            others = product.analog_group_id.product_ids - product
            product.analog_ids = others
            product.analog_count = len(others)

    def action_view_analogs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Analogs',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.analog_ids.ids)],
        }


class LostDemand(models.Model):
    """Lost demand: фіксація відмов через відсутність товару на складі."""
    _name = 'adealer.lost.demand'
    _description = 'Lost demand'
    _order = 'date desc, id desc'
    _rec_name = 'product_id'

    date = fields.Datetime('Date', default=fields.Datetime.now, required=True, index=True)
    product_id = fields.Many2one('product.template', 'Product', required=True, index=True)
    product_qty = fields.Float('Quantity', default=1.0)
    partner_id = fields.Many2one('res.partner', 'Customer')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    user_id = fields.Many2one('res.users', 'Manager', default=lambda self: self.env.user)
    reason = fields.Selection([
        ('out_of_stock', 'Out of stock'),
        ('price', 'Price not acceptable'),
        ('no_analog', 'No analog'),
        ('other', 'Other'),
    ], 'Reason', default='out_of_stock', required=True)
    note = fields.Text('Comment')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

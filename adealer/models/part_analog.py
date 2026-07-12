# -*- coding: utf-8 -*-
"""Аналоги (крос-номери) запчастин та облік упущеного попиту
(аналог 1С «Альфа-Авто»: РегистрСведений.ГруппыАналогов +
Обработка.ПодборНоменклатуры + Обработка/Отчет.УпущенныйСпрос).

Група аналогів об'єднує взаємозамінні деталі (оригінал + замінники різних
виробників). Із будь-якої деталі видно її аналоги і залишки по кожному —
щоб підібрати наявний замінник.
"""
from odoo import models, fields, api


class PartAnalogGroup(models.Model):
    _name = 'adealer.part.analog.group'
    _description = 'Група аналогів запчастин'
    _order = 'name'

    name = fields.Char('Назва групи', required=True,
                       help='Напр. «Фільтр масляний (двигун 1.6)»')
    note = fields.Text('Опис')
    product_ids = fields.One2many('product.template', 'analog_group_id', 'Аналоги')
    product_count = fields.Integer('К-сть аналогів', compute='_compute_product_count')
    active = fields.Boolean(default=True)

    @api.depends('product_ids')
    def _compute_product_count(self):
        for group in self:
            group.product_count = len(group.product_ids)


class ProductTemplateAnalog(models.Model):
    _inherit = 'product.template'

    analog_group_id = fields.Many2one('adealer.part.analog.group', 'Група аналогів',
                                      index=True,
                                      help='Взаємозамінні деталі в одній групі')
    analog_ids = fields.Many2many('product.template', string='Аналоги (замінники)',
                                  compute='_compute_analog_ids',
                                  help='Інші деталі з тієї ж групи аналогів')
    analog_count = fields.Integer('Аналогів', compute='_compute_analog_ids')

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
            'name': 'Аналоги',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.analog_ids.ids)],
        }


class LostDemand(models.Model):
    """Упущений попит: фіксація відмов через відсутність товару на складі."""
    _name = 'adealer.lost.demand'
    _description = 'Упущений попит'
    _order = 'date desc, id desc'
    _rec_name = 'product_id'

    date = fields.Datetime('Дата', default=fields.Datetime.now, required=True, index=True)
    product_id = fields.Many2one('product.template', 'Номенклатура', required=True, index=True)
    product_qty = fields.Float('Кількість', default=1.0)
    partner_id = fields.Many2one('res.partner', 'Клієнт')
    vehicle_id = fields.Many2one('fleet.vehicle', 'Автомобіль')
    user_id = fields.Many2one('res.users', 'Менеджер', default=lambda self: self.env.user)
    reason = fields.Selection([
        ('out_of_stock', 'Немає на складі'),
        ('price', 'Не влаштувала ціна'),
        ('no_analog', 'Немає аналога'),
        ('other', 'Інше'),
    ], 'Причина', default='out_of_stock', required=True)
    note = fields.Text('Коментар')
    company_id = fields.Many2one('res.company', 'Компанія', default=lambda self: self.env.company)

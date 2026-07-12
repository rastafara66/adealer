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
    _description = 'Сервісна кампанія'
    _inherit = ['mail.thread']
    _order = 'date_start desc, id desc'

    name = fields.Char('Назва кампанії', required=True, tracking=True)
    code = fields.Char('Код/номер', copy=False, index=True)
    campaign_type = fields.Selection([
        ('recall', 'Відкликання'),
        ('warranty', 'Гарантійна'),
        ('service', 'Сервісна акція'),
    ], 'Тип', default='recall', required=True, tracking=True)
    date_start = fields.Date('Дата початку', default=fields.Date.context_today)
    date_end = fields.Date('Дата завершення')
    state = fields.Selection([
        ('draft', 'Чернетка'),
        ('active', 'Активна'),
        ('closed', 'Закрита'),
    ], 'Стан', default='draft', required=True, tracking=True)
    description = fields.Html('Опис / інструкція')
    service_product_id = fields.Many2one('product.product', 'Робота по кампанії',
                                         domain="[('type', '=', 'service')]",
                                         help='Послуга, що виконується в межах кампанії')
    line_ids = fields.One2many('dealer.service.campaign.line', 'campaign_id', 'Автомобілі')
    vehicle_count = fields.Integer('Всього авто', compute='_compute_counts', store=True)
    done_count = fields.Integer('Виконано', compute='_compute_counts', store=True)
    progress = fields.Float('Прогрес, %', compute='_compute_counts', store=True)
    company_id = fields.Many2one('res.company', 'Компанія', default=lambda self: self.env.company)

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
            'name': _('Додати автомобілі'),
            'res_model': 'fleet.vehicle',
            'view_mode': 'list',
            'target': 'new',
        }


class ServiceCampaignLine(models.Model):
    _name = 'dealer.service.campaign.line'
    _description = 'Авто у сервісній кампанії'
    _order = 'state, id'

    campaign_id = fields.Many2one('dealer.service.campaign', 'Кампанія', required=True,
                                  ondelete='cascade', index=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Автомобіль', index=True)
    vin = fields.Char('VIN', help='VIN, якщо авто ще немає в базі')
    partner_id = fields.Many2one('res.partner', 'Власник')
    state = fields.Selection([
        ('pending', 'Очікує'),
        ('notified', 'Повідомлено'),
        ('done', 'Виконано'),
        ('rejected', 'Відмова клієнта'),
    ], 'Статус', default='pending', required=True, index=True)
    repair_order_id = fields.Many2one('repair.order', 'Наряд', copy=False,
                                      help='Наряд, яким закрито кампанію по авто')
    done_date = fields.Date('Дата виконання')

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
                                           string='Активні кампанії по авто')
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

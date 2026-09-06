# -*- coding: utf-8 -*-
"""Історія обслуговування авто and нагадування про ТО (аналог 1С «Альфа-Авто»:
Отчет.ИсторияАвтомобилей + Напоминания + звіт «Maintenance reminders»).

На картці авто клієнта (fleet.vehicle) показуємо всі його наряди, дату/пробіг
останнього обслуговування and розрахункову дату наступного ТО (за інтервалом).
Список авто, у яких ТО прострочене/наближається — для проактивних дзвінків.
"""
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _


class FleetVehicleServiceHistory(models.Model):
    _inherit = 'fleet.vehicle'

    repair_order_ids = fields.One2many('repair.order', 'vehicle_id', 'Repair orders')
    repair_order_count = fields.Integer('Orders count', compute='_compute_service_history',
                                        store=True)
    last_service_date = fields.Datetime('Last service',
                                        compute='_compute_service_history', store=True)
    last_service_mileage = fields.Float('Mileage at last service',
                                        compute='_compute_service_history', store=True)

    # Інтервали ТО (за замовчуванням 12 міс)
    service_interval_months = fields.Integer('Service interval, months', default=12)
    service_interval_km = fields.Float('Service interval, km')
    next_service_date = fields.Date('Next service (planned)',
                                    compute='_compute_next_service', store=True)
    service_due = fields.Boolean('Service due/overdue',
                                 compute='_compute_next_service', store=True,
                                 help='Estimated next service date ≤ today')

    @api.depends('repair_order_ids', 'repair_order_ids.create_date',
                 'repair_order_ids.mileage')
    def _compute_service_history(self):
        for veh in self:
            orders = veh.repair_order_ids
            veh.repair_order_count = len(orders)
            dates = orders.mapped('create_date')
            veh.last_service_date = max(dates) if dates else False
            mileages = [m for m in orders.mapped('mileage') if m]
            veh.last_service_mileage = max(mileages) if mileages else 0.0

    @api.depends('last_service_date', 'service_interval_months')
    def _compute_next_service(self):
        today = fields.Date.context_today(self)
        for veh in self:
            if veh.last_service_date and veh.service_interval_months:
                nxt = fields.Datetime.to_datetime(veh.last_service_date).date() + \
                    relativedelta(months=veh.service_interval_months)
                veh.next_service_date = nxt
                veh.service_due = nxt <= today
            else:
                veh.next_service_date = False
                veh.service_due = False

    def action_view_repair_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Service history'),
            'res_model': 'repair.order',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

# -*- coding: utf-8 -*-
"""Попередній запис на обслуговування (1С: регістр відомостей «ПредварительнаяЗапись»).

У 1С запис клієнта на СТО — це окремий об'єкт (регістр), НЕ наряд. Наряд-замовлення
може бути прив'язаний до запису (реквізит «Заказ»), а може й ні (клієнт записався, але
наряд ще не створено / не приїхав). Календар СТО будується саме на цих записах: по постах
(РабочееМесто) і часу, з тривалістю робіт.

Модель дзеркалить реквізити 1С-регістра:
  Період → appointment_datetime; РабочееМесто → workplace_id; Сотрудник → employee_id;
  ВремяРабот → work_duration; МП → advisor_id; ВремяПриемАМ → intake_time; Заказ →
  repair_order_id; Контрагент → partner_id; Автомобиль → vehicle_id; Модель → model_id;
  ГодВыпуска → year; ГосНомер → plate; Телефон → phone; ВинКод → vin;
  ЗаявленныеРаботы → requested_works; ВидРемонта → repair_type_id; УникальныйИдентификатор → guid_1c.
"""
from odoo import api, fields, models, _


class AdealerWorkplace(models.Model):
    _name = 'adealer.workplace'
    _description = 'Workplace / service post'
    _order = 'sequence, name'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer('Color')


class AdealerRepairType(models.Model):
    _name = 'adealer.repair.type'
    _description = 'Repair type'
    _order = 'name'

    name = fields.Char('Name', required=True, translate=True)
    code = fields.Char('Code')
    is_warranty = fields.Boolean('Warranty (unpaid)',
                                 help='Guarantee work — not charged to the customer')
    active = fields.Boolean(default=True)


class AdealerServiceBooking(models.Model):
    _name = 'adealer.service.booking'
    _description = 'Service booking (preliminary appointment)'
    _order = 'appointment_datetime desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char('Number', copy=False, default='/', index=True)
    appointment_datetime = fields.Datetime('Appointment date/time', required=True,
                                           default=fields.Datetime.now, tracking=True)
    stop_datetime = fields.Datetime('End', compute='_compute_stop', store=True)
    workplace_id = fields.Many2one('adealer.workplace', 'Workplace / post', index=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', 'Mechanic', index=True)
    advisor_id = fields.Many2one('hr.employee', 'Service advisor',
                                 help='МП — мастер-приёмщик')
    work_duration = fields.Float('Work duration, h', help='ВремяРабот', default=1.0)
    intake_time = fields.Char('Vehicle intake time', help='ВремяПриемАМ')

    sale_order_id = fields.Many2one('sale.order', 'Customer order', copy=False, index=True,
                                    help='Заказ — the customer order linked to this booking (1C: ЗаказПокупателя)')
    repair_order_id = fields.Many2one('repair.order', 'Repair order', copy=False, index=True,
                                      help='The repair order created from this booking (optional)')

    partner_id = fields.Many2one('res.partner', 'Customer', tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    model_id = fields.Many2one('fleet.vehicle.model', 'Model')
    year = fields.Char('Model year')
    plate = fields.Char('Plate number')
    phone = fields.Char('Phone')
    vin = fields.Char('VIN')
    requested_works = fields.Text('Requested works')
    repair_type_id = fields.Many2one('adealer.repair.type', 'Repair type')
    guid_1c = fields.Char('1C identifier', copy=False, index=True,
                          help='УникальныйИдентификатор — for sync idempotency')

    state = fields.Selection([
        ('draft', 'Planned'),
        ('confirmed', 'Confirmed'),
        ('arrived', 'Arrived'),
        ('done', 'Order created'),
        ('cancel', 'Cancelled'),
    ], default='draft', required=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.depends('appointment_datetime', 'work_duration')
    def _compute_stop(self):
        from datetime import timedelta
        for b in self:
            if b.appointment_datetime:
                b.stop_datetime = b.appointment_datetime + timedelta(hours=b.work_duration or 0.0)
            else:
                b.stop_datetime = False

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.model_id = self.vehicle_id.model_id
            self.vin = self.vehicle_id.vin_sn or self.vin
            if self.vehicle_id.partner_id:
                self.partner_id = self.vehicle_id.partner_id

    @api.onchange('partner_id')
    def _onchange_partner(self):
        if self.partner_id and not self.phone:
            self.phone = self.partner_id.phone or self.partner_id.mobile

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('adealer.service.booking') or '/'
        return super().create(vals_list)

    @api.depends('name', 'plate', 'vehicle_id', 'requested_works', 'partner_id')
    def _compute_display_name(self):
        for b in self:
            who = b.plate or (b.vehicle_id.name if b.vehicle_id else '') or (b.partner_id.name if b.partner_id else '')
            works = (b.requested_works or '').strip().replace('\n', ' ')
            if len(works) > 30:
                works = works[:30] + '…'
            parts = [b.name or '/']
            if who:
                parts.append(who)
            if works:
                parts.append(works)
            b.display_name = ' · '.join(parts)

    def action_create_repair_order(self):
        """Створити наряд-замовлення з запису й прив'язати (реквізит Заказ)."""
        self.ensure_one()
        if self.repair_order_id:
            ro = self.repair_order_id
        else:
            ro = self.env['repair.order'].create({
                'partner_id': self.partner_id.id,
                'vehicle_id': self.vehicle_id.id,
                'schedule_date': self.appointment_datetime,
            })
            self.repair_order_id = ro.id
            self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'res_id': ro.id,
            'view_mode': 'form',
            'target': 'current',
        }


class RepairOrderBooking(models.Model):
    _inherit = 'repair.order'

    booking_id = fields.Many2one('adealer.service.booking', 'Service booking', copy=False, index=True,
                                 help='The preliminary appointment this order was created from')

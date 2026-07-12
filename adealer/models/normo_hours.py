# -*- coding: utf-8 -*-
"""Standard hours у наряді (як у 1С: у ЗаказНаряд «Quantity» рядка-роботи —
це і є нормо-години; окремого поля/сутності не треба).

- repair.line.normo_hours — для рядків-послуг дорівнює кількості (нормо-годинам),
  для запчастин = 0. Обчислюється, але можна відкоригувати вручну.
- Виконавці — це Mechanics наряду (repair.order.mechanic_ids), кілька hr.employee.
- repair.order.total_normo_hours — сумарні нормо-години наряду.

Заповнюється автоматично зі штатного імпорту (кількість рядка вже імпортується),
а перерахунок при оновленні модуля проставляє нормо-години наявним нарядам.
"""
from odoo import models, fields, api


class RepairLineNormo(models.Model):
    _inherit = 'repair.line'

    normo_hours = fields.Float('Standard hours', digits=(12, 2),
                               compute='_compute_normo_hours', store=True, readonly=False,
                               help='Line standard hours. For services = quantity (in 1C the '
                                    'work quantity = standard hours); can be adjusted manually')

    @api.depends('product_id', 'product_id.type', 'product_uom_qty')
    def _compute_normo_hours(self):
        for line in self:
            is_service = line.product_id and line.product_id.type == 'service'
            line.normo_hours = (line.product_uom_qty or 0.0) if is_service else 0.0


class RepairOrderNormo(models.Model):
    _inherit = 'repair.order'

    total_normo_hours = fields.Float('Total standard hours', compute='_compute_total_normo_hours',
                                     store=True, digits=(12, 2))

    @api.depends('operations.normo_hours')
    def _compute_total_normo_hours(self):
        for order in self:
            order.total_normo_hours = sum(order.operations.mapped('normo_hours'))

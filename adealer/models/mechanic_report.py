# -*- coding: utf-8 -*-
"""Звіт «Mechanic output» (аналог 1С «Альфа-Авто»: Отчет.Выработка /
ВыработкаИсполнителей / СтатистикаПоРаботам).

SQL-в'юха to сервісних рядках нарядів у розрізі механіків наряду
(repair.order.mechanic_ids). Якщо на наряді кілька механіків — нормо-години
й сума рядка діляться порівну between ними (щоб підсумки сходились з нарядом).
Доступна як pivot/graph/list для гнучкого аналізу.
"""
from odoo import models, fields, tools


class MechanicOutputReport(models.Model):
    _name = 'adealer.mechanic.output.report'
    _description = 'Mechanic output'
    _auto = False
    _order = 'date desc'

    mechanic_id = fields.Many2one('hr.employee', 'Performer', readonly=True)
    repair_id = fields.Many2one('repair.order', 'Order', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    product_id = fields.Many2one('product.product', 'Work/service', readonly=True)
    date = fields.Date('Date', readonly=True)
    normo_hours = fields.Float('Standard hours', readonly=True)
    amount = fields.Float('Amount', readonly=True)
    line_count = fields.Integer('Works count', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # rel — таблиця many2many механіків наряду (repair.order.mechanic_ids).
        # mc.cnt — скільки механіків на наряді (для рівного поділу).
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    row_number() OVER (ORDER BY rl.id, rel.hr_employee_id) AS id,
                    rel.hr_employee_id          AS mechanic_id,
                    rl.repair_id                AS repair_id,
                    ro.vehicle_id               AS vehicle_id,
                    ro.partner_id               AS partner_id,
                    rl.product_id               AS product_id,
                    ro.create_date::date        AS date,
                    COALESCE(rl.normo_hours, 0) / mc.cnt    AS normo_hours,
                    COALESCE(rl.price_subtotal, 0) / mc.cnt AS amount,
                    1                           AS line_count
                FROM repair_line rl
                JOIN repair_order ro    ON ro.id = rl.repair_id
                JOIN product_product pp ON pp.id = rl.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id
                JOIN hr_employee_repair_order_rel rel ON rel.repair_order_id = ro.id
                JOIN (
                    SELECT repair_order_id, COUNT(*)::numeric AS cnt
                    FROM hr_employee_repair_order_rel
                    GROUP BY repair_order_id
                ) mc ON mc.repair_order_id = ro.id
                WHERE pt.type = 'service'
            )
        """ % (self._table,))

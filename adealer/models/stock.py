from odoo import models, fields, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    parts_arrival_notified = fields.Boolean(
        string='Parts arrival notified', default=False, copy=False)

    def _action_done(self):
        res = super()._action_done()
        # Тригер як у 1С: проведення приходу ЗЧ (incoming) -> перевірити,
        # які замовлення покупця стали забезпеченими, і створити оповіщення.
        incoming = self.filtered(lambda p: p.picking_type_code == 'incoming')
        if incoming:
            incoming._notify_parts_arrival()
        return res

    def _notify_parts_arrival(self):
        received_products = self.move_ids.product_id
        if not received_products:
            return
        deliveries = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'assigned'),
            ('sale_id', '!=', False),
            ('parts_arrival_notified', '=', False),
        ])
        for delivery in deliveries:
            if delivery.move_ids.product_id & received_products:
                delivery._schedule_parts_arrival_activity()

    def _schedule_parts_arrival_activity(self):
        self.ensure_one()
        sale_order = self.sale_id
        if not sale_order:
            return

        repair = self.env['repair.order'].search(
            [('source_sale_order_id', '=', sale_order.id)], limit=1)
        ref = _("наряд №%s") % repair.name if repair else _("замовлення %s") % sale_order.name
        summary = _("Надійшли ЗЧ — можна відвантажити")
        note = _("Надійшли запчастини. Замовлення %(order)s забезпечене, можна відвантажити (%(ref)s).") % {
            'order': sale_order.name,
            'ref': ref,
        }
        user = sale_order.user_id or self.env.user
        target = repair or sale_order
        target.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=summary,
            note=note,
            user_id=user.id,
        )
        self.parts_arrival_notified = True

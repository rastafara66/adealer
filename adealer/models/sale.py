from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', index=True)
    vehicle_logo = fields.Image(related='vehicle_id.display_logo', string='Vehicle Logo', readonly=True)
    # ? domain="[('partner_id', '=', 'partner_id')]",

    repair_order_ids = fields.One2many(
        'repair.order', 'source_sale_order_id', string='Repair Orders')
    repair_order_count = fields.Integer(
        string='Repair Order Count', compute='_compute_repair_order_count')

    @api.depends('repair_order_ids')
    def _compute_repair_order_count(self):
        for order in self:
            order.repair_order_count = len(order.repair_order_ids)

    def action_create_repair_order(self):
        """Create order (repair.order) на основі замовлення покупця.
        Аналог 1С ОбработкаЗаполнения: копіює партнера, авто and рядки."""
        self.ensure_one()
        if not self.vehicle_id:
            raise UserError(_("No vehicle is specified on the order."))

        operations = []
        for line in self.order_line:
            if line.display_type or not line.product_id:
                continue
            operations.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom_id.id,
                'price_unit': line.price_unit,
                'tax_id': [(6, 0, line.tax_ids.ids)],
                'currency_id': self.currency_id.id,
            }))

        repair = self.env['repair.order'].create({
            'partner_id': self.partner_id.id,
            'vehicle_id': self.vehicle_id.id,
            'company_id': self.company_id.id,
            'source_sale_order_id': self.id,
            'operations': operations,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Order'),
            'res_model': 'repair.order',
            'view_mode': 'form',
            'res_id': repair.id,
        }

    def action_view_repair_orders(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Repair orders'),
            'res_model': 'repair.order',
            'domain': [('source_sale_order_id', '=', self.id)],
        }
        if self.repair_order_count == 1:
            action.update(view_mode='form', res_id=self.repair_order_ids.id)
        else:
            action.update(view_mode='list,form')
        return action

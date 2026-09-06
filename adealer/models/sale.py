from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', index=True)
    vehicle_logo = fields.Image(related='vehicle_id.display_logo', string='Vehicle Logo', readonly=True)
    # ? domain="[('partner_id', '=', 'partner_id')]",

    # Same keys as core, different labels. Here the document is the customer's
    # order TO US, so the core wording ("Quotation" / "Quotation Sent" /
    # "Sales Order") described the opposite direction and misled users into
    # thinking we were about to email out an offer.
    state = fields.Selection(selection=[
        ('draft', "Being drawn up"),
        ('sent', "Agreed with customer"),
        ('sale', "Confirmed"),
        ('cancel', "Cancelled"),
    ])

    # Must NOT be named repair_order_ids: the core `repair` module already
    # defines that field on sale.order (inverse sale_order_id). Overriding it
    # broke the core "Repairs" stat button, which then counted our own records
    # and appeared as a duplicate of the button below.
    own_repair_order_ids = fields.One2many(
        'repair.order', 'source_sale_order_id', string='Repair Orders')
    own_repair_order_count = fields.Integer(
        string='Repair Order Count', compute='_compute_own_repair_order_count')

    @api.depends('own_repair_order_ids')
    def _compute_own_repair_order_count(self):
        for order in self:
            order.own_repair_order_count = len(order.own_repair_order_ids)

    @api.depends('name')
    def _compute_display_name(self):
        """Name the document kind in breadcrumbs and m2o fields,
        so "Customer order No. 3455" is not confused with the repair order
        it produced. Same rationale as repair.order._compute_display_name."""
        for order in self:
            order.display_name = _("Customer order No. %s") % (order.name or '/')

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
        if self.own_repair_order_count == 1:
            action.update(view_mode='form', res_id=self.own_repair_order_ids.id)
        else:
            action.update(view_mode='tree,form')
        return action

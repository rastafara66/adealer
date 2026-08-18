# service.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    operations = fields.One2many(
        'repair.line', 'repair_id', 'Operations',
        copy=True, readonly=False)
    # Дві відфільтровані «проекції» тих самих рядків (operations) для вкладок:
    # послуги (type='service') і запчастини (товари, type!='service').
    service_line_ids = fields.One2many(
        'repair.line', 'repair_id', string='Service operations',
        domain=[('product_type', '=', 'service')], copy=False, readonly=False)
    part_line_ids = fields.One2many(
        'repair.line', 'repair_id', string='Service parts',
        domain=[('product_type', '!=', 'service')], copy=False, readonly=False)
    partner_id = fields.Many2one(
        'res.partner', 'Customer')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', index=True)
    vehicle_logo = fields.Image(related='vehicle_id.display_logo', string='Vehicle Logo', readonly=True)
    mechanic_ids = fields.Many2many('hr.employee', string='Mechanics',
        help='Work performers on the order (executors)')
    mileage = fields.Float(
        'Mileage', help='Vehicle mileage at intake (vehicle mileage at intake)')
    service_advisor_id = fields.Many2one(
        'res.users', string='Manager',
        help='Order manager / responsible')
    source_sale_order_id = fields.Many2one(
        'sale.order', string='Source Sale Order', copy=False, index=True,
        help='The sale order this repair order was created from')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True)
    amount_total = fields.Monetary(
        string='Amount', compute='_compute_amount_total', store=True,
        currency_field='currency_id', help='Total order amount (from operation lines)')

    @api.depends('operations.price_subtotal')
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = sum(order.operations.mapped('price_subtotal'))

    @api.depends('name')
    def _compute_display_name(self):
        """Name the document kind in breadcrumbs and m2o fields.
        A bare "1704" was ambiguous once several documents of the chain
        (order -> repair order -> invoice) sat next to each other."""
        for order in self:
            order.display_name = _("Repair order No. %s") % (order.name or '/')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = vals.get('name') or '/'
            if vals['name'].startswith('/'):
                vals['name'] = (self.env['ir.sequence'].next_by_code(
                    'repair.order') or '/') + vals['name']
                vals['name'] = vals['name'][:-1] if vals['name'].endswith(
                    '/') and vals['name'] != '/' else vals['name']
        return super(RepairOrder, self).create(vals_list)

    def write(self, vals):
        if 'driver_id' in vals and vals['driver_id']:
            driver_id = vals['driver_id']
            self.filtered(lambda v: v.driver_id.id != driver_id).create_driver_history(driver_id)
        return super(RepairOrder, self).write(vals)

    def _check_parts_availability(self):
        """Контроль залишків ЗЧ в операціях наряду (аналог 1С КонтрольОстатков).
        Блокує, якщо вільного залишку складського товару недостатньо."""
        Warehouse = self.env['stock.warehouse']
        for repair in self:
            warehouse = Warehouse.search([('company_id', '=', repair.company_id.id)], limit=1)
            if not warehouse:
                continue
            shortages = []
            for op in repair.operations:
                product = op.product_id
                if not product or not product.is_storable:
                    continue
                needed = op.product_uom_qty
                if op.product_uom and op.product_uom != product.uom_id:
                    needed = op.product_uom._compute_quantity(op.product_uom_qty, product.uom_id)
                free = product.with_context(warehouse_id=warehouse.id).free_qty
                if free < needed:
                    shortages.append(_("• %(product)s: needed %(need)s, available %(free)s") % {
                        'product': product.display_name,
                        'need': needed,
                        'free': free,
                    })
            if shortages:
                raise UserError(
                    _("Not enough parts in warehouse \"%(wh)s\":\n%(list)s") % {
                        'wh': warehouse.display_name,
                        'list': "\n".join(shortages),
                    })

    def action_validate(self):
        self._check_parts_availability()
        return super().action_validate()

class RepairLine(models.Model):
    _name = 'repair.line'
    _description = 'Repair Line'

    repair_id = fields.Many2one('repair.order', string='Repair Order', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    # тип товару (для розділення на вкладки Parts/Service operations); store -> для domain
    product_type = fields.Selection(related='product_id.type', store=True, string='Type')
    product_uom_qty = fields.Float(string='Quantity', default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
    price_unit = fields.Float(string='Unit Price')
    discount = fields.Float(string='Discount (%)', default=0.0)
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)
    tax_id = fields.Many2many('account.tax', string='Taxes')
    currency_id = fields.Many2one('res.currency', string='Currency')

    @api.depends('product_uom_qty', 'price_unit', 'discount')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_uom_qty * line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Підставити ціну з прайс-листа партнера (аналог 1С ПолучитьЦенуНаСервере)."""
        if not self.product_id:
            return
        self.product_uom = self.product_id.uom_id
        self.tax_id = self.product_id.taxes_id
        partner = self.repair_id.partner_id
        pricelist = partner.property_product_pricelist if partner else False
        qty = self.product_uom_qty or 1.0
        if pricelist:
            self.price_unit = pricelist._get_product_price(self.product_id, qty)
        else:
            self.price_unit = self.product_id.list_price

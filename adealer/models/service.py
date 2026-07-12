# service.py

import os
import json
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
        'repair.line', 'repair_id', string='Сервісні операції',
        domain=[('product_type', '=', 'service')], copy=False, readonly=False)
    part_line_ids = fields.One2many(
        'repair.line', 'repair_id', string='Запчастини',
        domain=[('product_type', '!=', 'service')], copy=False, readonly=False)
    partner_id = fields.Many2one(
        'res.partner', 'Customer')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, index=True)
    vehicle_logo = fields.Image(related='vehicle_id.display_logo', string='Vehicle Logo', readonly=True)
    mechanic_ids = fields.Many2many('hr.employee', string='Механіки',
        help='Виконавці робіт по наряду (ИсполнителиРабот з 1С)')
    mileage = fields.Float(
        'Пробіг', help='Пробіг авто на момент приймання (аналог поля 1С ЗаказНаряд.Пробег)')
    service_advisor_id = fields.Many2one(
        'res.users', string='Менеджер',
        help='Менеджер/відповідальний наряду (1С: Ответственный)')
    source_sale_order_id = fields.Many2one(
        'sale.order', string='Source Sale Order', copy=False, index=True,
        help='Замовлення покупця, з якого створено цей наряд')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True)
    amount_total = fields.Monetary(
        string='Сума', compute='_compute_amount_total', store=True,
        currency_field='currency_id', help='Загальна сума наряду (з рядків операцій)')

    @api.depends('operations.price_subtotal')
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = sum(order.operations.mapped('price_subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')
        os.makedirs(log_dir, exist_ok=True)
        file_path = os.path.join(log_dir, 'repairs.json')

        for vals in vals_list:
            vals['name'] = vals.get('name') or '/'
            if vals['name'].startswith('/'):
                vals['name'] = (self.env['ir.sequence'].next_by_code(
                    'repair.order') or '/') + vals['name']
                vals['name'] = vals['name'][:-1] if vals['name'].endswith(
                    '/') and vals['name'] != '/' else vals['name']

            operations_for_log = []
            if 'operations' in vals and vals['operations']:
                for op_command in vals['operations']:
                    if op_command[0] == 0 and len(op_command) == 3:
                        op_vals = op_command[2]
                        operations_for_log.append({
                            'product_id': op_vals.get('product_id'),
                            'product_uom_qty': op_vals.get('product_uom_qty')
                        })
                    elif op_command[0] == 1 and len(op_command) == 3:
                        op_vals = op_command[2]
                        operations_for_log.append({
                            'id': op_command[1],
                            'product_id': op_vals.get('product_id'),
                            'product_uom_qty': op_vals.get('product_uom_qty')
                        })
                    elif op_command[0] == 4 and len(op_command) == 2:
                        operations_for_log.append({'id': op_command[1]})

            product_type_name = None
            if 'product_id' in vals and vals['product_id']:
                product_type_name = self.env['product.product'].browse(vals['product_id']).name

            vehicle_name = None
            if 'vehicle_id' in vals and vals['vehicle_id']:
                vehicle_name = self.env['fleet.vehicle'].browse(vals['vehicle_id']).name

            jsonstr = json.dumps([
                {'name': vals.get('name')},
                {'repair_type': product_type_name},
                {'vehicle_id': vehicle_name},
                {'operations': operations_for_log}
            ])

            with open(file_path, 'a') as f:
                f.write('create ' + jsonstr + '\n')

        return super(RepairOrder, self).create(vals_list)

    def write(self, vals):
        if 'driver_id' in vals and vals['driver_id']:
            driver_id = vals['driver_id']
            self.filtered(lambda v: v.driver_id.id != driver_id).create_driver_history(driver_id)

        operations_for_log = []
        if 'operations' in vals and vals['operations']:
            for op_command in vals['operations']:
                if op_command[0] == 0 and len(op_command) == 3:
                    op_vals = op_command[2]
                    operations_for_log.append({
                        'product_id': op_vals.get('product_id'),
                        'product_uom_qty': op_vals.get('product_uom_qty')
                    })
                elif op_command[0] == 1 and len(op_command) == 3:
                    op_vals = op_command[2]
                    operations_for_log.append({
                        'id': op_command[1],
                        'product_id': op_vals.get('product_id'),
                        'product_uom_qty': op_vals.get('product_uom_qty')
                    })
                elif op_command[0] == 4 and len(op_command) == 2:
                    operations_for_log.append({'id': op_command[1]})
                elif op_command[0] == 2 and len(op_command) == 2:
                    operations_for_log.append({'deleted_id': op_command[1]})
        elif hasattr(self, 'operations') and self.operations:
            for op_record in self.operations:
                operations_for_log.append({
                    'product_id': op_record.product_id.id if op_record.product_id else None,
                    'product_uom_qty': op_record.product_uom_qty
                })

        current_name = vals.get('name', self.name)
        current_product_type_name = None
        if 'product_id' in vals and vals['product_id']:
            current_product_type_name = self.env['product.product'].browse(vals['product_id']).name
        elif self.product_id:
            current_product_type_name = self.product_id.name

        current_vehicle_name = None
        if 'vehicle_id' in vals and vals['vehicle_id']:
            current_vehicle_name = self.env['fleet.vehicle'].browse(vals['vehicle_id']).name
        elif self.vehicle_id:
            current_vehicle_name = self.vehicle_id.name

        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'log')
        os.makedirs(log_dir, exist_ok=True)
        jsonstr = json.dumps([
            {'name': current_name},
            {'repair_type': current_product_type_name},
            {'vehicle_id': current_vehicle_name},
            {'operations': operations_for_log}
        ])

        file_path = os.path.join(log_dir, 'repairs.json')
        with open(file_path, 'a') as f:
            f.write('write ' + jsonstr + '\n')

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
                    shortages.append(_("• %(product)s: потрібно %(need)s, вільно %(free)s") % {
                        'product': product.display_name,
                        'need': needed,
                        'free': free,
                    })
            if shortages:
                raise UserError(
                    _("Недостатньо запчастин на складі «%(wh)s»:\n%(list)s") % {
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
    # тип товару (для розділення на вкладки Запчастини/Сервісні операції); store -> для domain
    product_type = fields.Selection(related='product_id.type', store=True, string='Тип')
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

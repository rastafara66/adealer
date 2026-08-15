# -*- coding: utf-8 -*-
"""Склад автомобілів для продажу — облік авто як окремої облікової одиниці
(за VIN): статуси, варіанти комплектації, опції, кольори, ціни.

Ключова відмінність від fleet.vehicle: fleet.vehicle описує авто КЛІЄНТА
(на обслуговуванні), а dealer.car — це товарний запас авто АВТОСАЛОНУ на
продаж, зі своїм життєвим циклом: замовлено → в дорозі → на складі →
резерв → продано → видано. Після продажу авто може бути зареєстроване як
fleet.vehicle клієнта (fleet_vehicle_id).
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CarColor(models.Model):
    _name = 'dealer.car.color'
    _description = 'Vehicle color'
    _order = 'name'

    name = fields.Char('Color', required=True, translate=True)
    code = fields.Char('Color code', help='Manufacturer color code')
    is_metallic = fields.Boolean('Metallic')
    active = fields.Boolean(default=True)


class CarComplectation(models.Model):
    """Варіант комплектації моделі."""
    _name = 'dealer.car.complectation'
    _description = 'Trim / configuration'
    _order = 'model_id, name'

    name = fields.Char('Trim / configuration', required=True,
                       help='e.g. Trend, Titanium, ST-Line')
    code = fields.Char('Code')
    model_id = fields.Many2one('fleet.vehicle.model', 'Model', index=True)
    base_price = fields.Monetary('Base price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.company.currency_id)
    option_ids = fields.Many2many('dealer.car.option', string='Options in the trim')
    note = fields.Text('Description')
    active = fields.Boolean(default=True)


class CarOption(models.Model):
    """Option/додаткове обладнання авто."""
    _name = 'dealer.car.option'
    _description = 'Vehicle option'
    _order = 'category, name'

    name = fields.Char('Option', required=True, translate=True)
    code = fields.Char('Code')
    category = fields.Char('Group', help='e.g. Safety, Comfort, Multimedia')
    price = fields.Monetary('Option price', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(default=True)


class CarStatusHistory(models.Model):
    _name = 'dealer.car.status.history'
    _description = 'Vehicle status history'
    _order = 'change_date desc, id desc'

    car_id = fields.Many2one('dealer.car', 'Vehicle', required=True,
                             ondelete='cascade', index=True)
    status = fields.Char('Status')
    change_date = fields.Datetime('Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)


class DealerCar(models.Model):
    _name = 'dealer.car'
    _description = 'Vehicle (showroom stock)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Name', compute='_compute_name', store=True)
    vin = fields.Char('VIN', copy=False, index=True, tracking=True,
                      help='Vehicle identification number (unique)')
    model_id = fields.Many2one('fleet.vehicle.model', 'Model',
                               tracking=True, index=True,
                               help='Optional: matched fleet model. Imported cars may carry '
                                    'the model as text in "Model (text)" instead.')
    model_name_1c = fields.Char('Model (text)',
                                help='Model description as text (when no fleet model matched)')
    brand_id = fields.Many2one(related='model_id.brand_id', store=True, string='Brand')
    brand_logo = fields.Image(related='model_id.brand_id.image_128', string='Logo', readonly=True)
    image_1920 = fields.Image('Main photo', max_width=1920, max_height=1920)
    image_128 = fields.Image('Main photo (thumb)', related='image_1920',
                             max_width=128, max_height=128, store=True)
    image_ids = fields.One2many('dealer.car.image', 'car_id', 'Photos')
    image_count = fields.Integer(compute='_compute_image_count')
    complectation_id = fields.Many2one('dealer.car.complectation', 'Trim / configuration',
                                       domain="[('model_id', '=', model_id)]")
    color_id = fields.Many2one('dealer.car.color', 'Color')
    option_ids = fields.Many2many('dealer.car.option', string='Options')
    model_year = fields.Integer('Model year')
    engine_volume = fields.Integer('Engine displacement, cc')
    transmission = fields.Selection([
        ('manual', 'Manual'), ('auto', 'Automatic'),
        ('robot', 'Automated'), ('cvt', 'CVT'),
    ], 'Transmission')

    status = fields.Selection([
        ('ordered', 'Ordered'),
        ('in_transit', 'In transit'),
        ('in_stock', 'In stock'),
        ('reserved', 'Reserve'),
        ('sold', 'Sold'),
        ('delivered', 'Delivered to customer'),
    ], 'Status', default='ordered', required=True, tracking=True, index=True,
        group_expand='_expand_status')
    status_history_ids = fields.One2many('dealer.car.status.history', 'car_id', 'Status history')

    is_trade_in = fields.Boolean('Trade-in', tracking=True,
                                 help='Vehicle accepted as trade-in')

    # Prices
    purchase_price = fields.Monetary('Purchase price', currency_field='currency_id')
    sale_price = fields.Monetary('Sale price', currency_field='currency_id', tracking=True)
    options_price = fields.Monetary('Options amount', compute='_compute_options_price',
                                    store=True, currency_field='currency_id')
    total_price = fields.Monetary('Total due', compute='_compute_total_price',
                                  store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Контрагенти / документи
    supplier_id = fields.Many2one('res.partner', 'Supplier',
                                  domain="[('supplier_rank', '>', 0)]")
    partner_id = fields.Many2one('res.partner', 'Buyer', tracking=True)
    sale_order_id = fields.Many2one('sale.order', 'Sale order', copy=False)
    sale_date = fields.Date('Sale date', copy=False,
                            help='Date the vehicle was sold (from the sale document)')
    sale_move_id = fields.Many2one('account.move', 'Sale invoice', copy=False, index=True,
                                   help='The delivery note / invoice this vehicle was sold on')
    vin_1c = fields.Char('Import VIN key', copy=False, index=True,
                         help='VIN as imported from the source vehicle catalog (dedup key)')
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', 'Customer vehicle (fleet)', copy=False,
                                       help='Created when the vehicle is delivered to the customer')

    location_note = fields.Char('Storage location')
    note = fields.Text('Notes')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('vin_uniq', 'unique(vin)', 'A vehicle with this VIN already exists in stock.'),
    ]

    @api.model
    def _expand_status(self, statuses, domain):
        return [s[0] for s in type(self).status.selection]

    @api.depends('model_id.brand_id.name', 'model_id.name', 'model_name_1c', 'vin', 'color_id.name')
    def _compute_name(self):
        for car in self:
            parts = [car.model_id.brand_id.name or '', car.model_id.name or '']
            label = '/'.join(p for p in parts if p) or (car.model_name_1c or '')
            if car.color_id:
                label = '%s (%s)' % (label, car.color_id.name)
            if car.vin:
                label = '%s — %s' % (label, car.vin)
            car.name = label or _('New vehicle')

    @api.depends('option_ids.price')
    def _compute_options_price(self):
        for car in self:
            car.options_price = sum(car.option_ids.mapped('price'))

    @api.depends('image_1920', 'image_ids')
    def _compute_image_count(self):
        for car in self:
            car.image_count = (1 if car.image_1920 else 0) + len(car.image_ids)

    @api.depends('sale_price', 'options_price')
    def _compute_total_price(self):
        for car in self:
            car.total_price = (car.sale_price or 0.0) + (car.options_price or 0.0)

    @api.onchange('complectation_id')
    def _onchange_complectation_id(self):
        if self.complectation_id:
            if self.complectation_id.base_price and not self.sale_price:
                self.sale_price = self.complectation_id.base_price
            if self.complectation_id.option_ids:
                self.option_ids = [(6, 0, self.complectation_id.option_ids.ids)]

    def _set_status(self, new_status):
        for car in self:
            if car.status != new_status:
                self.env['dealer.car.status.history'].create({
                    'car_id': car.id,
                    'status': dict(type(self).status.selection).get(new_status),
                })
            car.status = new_status

    # --- кнопки життєвого циклу ---
    def action_set_in_transit(self):
        self._set_status('in_transit')

    def action_receive(self):
        """Прийняти авто на склад (аналог ПоступлениеАвтомобилей)."""
        self._set_status('in_stock')

    def action_reserve(self):
        if any(c.status not in ('in_stock',) for c in self):
            raise UserError(_('Only a vehicle with status "In stock" can be reserved.'))
        self._set_status('reserved')

    def action_unreserve(self):
        self._set_status('in_stock')

    def action_sell(self):
        """Sell авто (аналог РеализацияАвтомобилей)."""
        for car in self:
            if not car.partner_id:
                raise UserError(_('Specify the buyer before selling the vehicle.'))
        self._set_status('sold')

    def action_deliver(self):
        """Видати авто клієнту і завести його як fleet.vehicle клієнта."""
        for car in self:
            if car.status != 'sold':
                raise UserError(_('Only a sold vehicle can be delivered.'))
            if not car.fleet_vehicle_id:
                car.fleet_vehicle_id = self.env['fleet.vehicle'].create({
                    'model_id': car.model_id.id,
                    'vin_sn': car.vin,
                    'partner_id': car.partner_id.id,
                    'driver_id': car.partner_id.id,
                    'model_year': str(car.model_year) if car.model_year else False,
                }).id
            car._set_status('delivered')

    def action_view_fleet_vehicle(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle',
            'res_id': self.fleet_vehicle_id.id,
            'view_mode': 'form',
        }

    def action_view_sale_move(self):
        """Відкрити документ продажу (Реалізацію) цього авто."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale invoice'),
            'res_model': 'account.move',
            'res_id': self.sale_move_id.id,
            'view_mode': 'form',
        }

    @api.model
    def find_by_vin(self, vin):
        if not vin:
            return self.browse()
        return self.search([('vin', '=', vin.strip())], limit=1)


class AccountMoveVehicle(models.Model):
    """Позначка «продаж авто» на Реалізації + перелік проданих у ній машин."""
    _inherit = 'account.move'

    dealer_car_ids = fields.One2many('dealer.car', 'sale_move_id', string='Vehicles sold')
    is_vehicle_sale = fields.Boolean('Vehicle sale', compute='_compute_vehicle_sale',
                                     store=True, index=True,
                                     help='This delivery note sells at least one vehicle')
    dealer_car_count = fields.Integer('Vehicles', compute='_compute_vehicle_sale', store=True)

    @api.depends('dealer_car_ids')
    def _compute_vehicle_sale(self):
        for move in self:
            move.dealer_car_count = len(move.dealer_car_ids)
            move.is_vehicle_sale = bool(move.dealer_car_ids)

    def action_view_dealer_cars(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Vehicles sold'),
            'res_model': 'dealer.car',
            'domain': [('sale_move_id', '=', self.id)],
            'view_mode': 'list,form',
        }

# -*- coding: utf-8 -*-
"""Склад автомобілів для продажу (аналог 1С «Альфа-Авто»: облік авто як
окремої облікової одиниці — РегистрНакопления.ОстаткиАвтомобилей,
Справочник.Автомобили в розрізі VIN, СтатусыАвтомобилей, ЖурналСостояний,
ВариантыКомплектации, Опции, ЦеныОпций, Цвета).

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
    _description = 'Колір автомобіля'
    _order = 'name'

    name = fields.Char('Колір', required=True, translate=True)
    code = fields.Char('Код кольору', help='Код кольору виробника')
    is_metallic = fields.Boolean('Металік')
    active = fields.Boolean(default=True)


class CarComplectation(models.Model):
    """Варіант комплектації моделі (ВариантыКомплектации)."""
    _name = 'dealer.car.complectation'
    _description = 'Комплектація'
    _order = 'model_id, name'

    name = fields.Char('Комплектація', required=True,
                       help='Напр. Trend, Titanium, ST-Line')
    code = fields.Char('Код')
    model_id = fields.Many2one('fleet.vehicle.model', 'Модель', index=True)
    base_price = fields.Monetary('Базова ціна', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Валюта',
                                  default=lambda self: self.env.company.currency_id)
    option_ids = fields.Many2many('dealer.car.option', string='Опції у комплектації')
    note = fields.Text('Опис')
    active = fields.Boolean(default=True)


class CarOption(models.Model):
    """Опція/додаткове обладнання авто (Опции + ЦеныОпций)."""
    _name = 'dealer.car.option'
    _description = 'Опція автомобіля'
    _order = 'category, name'

    name = fields.Char('Опція', required=True, translate=True)
    code = fields.Char('Код')
    category = fields.Char('Група', help='Напр. Безпека, Комфорт, Мультимедіа')
    price = fields.Monetary('Ціна опції', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Валюта',
                                  default=lambda self: self.env.company.currency_id)
    active = fields.Boolean(default=True)


class CarStatusHistory(models.Model):
    _name = 'dealer.car.status.history'
    _description = 'Історія статусів авто'
    _order = 'change_date desc, id desc'

    car_id = fields.Many2one('dealer.car', 'Автомобіль', required=True,
                             ondelete='cascade', index=True)
    status = fields.Char('Статус')
    change_date = fields.Datetime('Дата', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', 'Користувач', default=lambda self: self.env.user)


class DealerCar(models.Model):
    _name = 'dealer.car'
    _description = 'Автомобіль (склад автосалону)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Назва', compute='_compute_name', store=True)
    vin = fields.Char('VIN', copy=False, index=True, tracking=True,
                      help='Ідентифікаційний номер кузова (унікальний)')
    model_id = fields.Many2one('fleet.vehicle.model', 'Модель', required=True,
                               tracking=True, index=True)
    brand_id = fields.Many2one(related='model_id.brand_id', store=True, string='Марка')
    brand_logo = fields.Image(related='model_id.brand_id.image_128', string='Лого', readonly=True)
    complectation_id = fields.Many2one('dealer.car.complectation', 'Комплектація',
                                       domain="[('model_id', '=', model_id)]")
    color_id = fields.Many2one('dealer.car.color', 'Колір')
    option_ids = fields.Many2many('dealer.car.option', string='Опції')
    model_year = fields.Integer('Рік випуску')
    engine_volume = fields.Integer('Обʼєм двигуна, см³')
    transmission = fields.Selection([
        ('manual', 'Механічна'), ('auto', 'Автоматична'),
        ('robot', 'Робот'), ('cvt', 'Варіатор'),
    ], 'КПП')

    status = fields.Selection([
        ('ordered', 'Замовлено'),
        ('in_transit', 'В дорозі'),
        ('in_stock', 'На складі'),
        ('reserved', 'Резерв'),
        ('sold', 'Продано'),
        ('delivered', 'Видано клієнту'),
    ], 'Статус', default='ordered', required=True, tracking=True, index=True,
        group_expand='_expand_status')
    status_history_ids = fields.One2many('dealer.car.status.history', 'car_id', 'Історія статусів')

    is_trade_in = fields.Boolean('Trade-in', tracking=True,
                                 help='Авто прийняте в залік (Trade-in)')

    # Ціни
    purchase_price = fields.Monetary('Ціна закупки', currency_field='currency_id')
    sale_price = fields.Monetary('Ціна продажу', currency_field='currency_id', tracking=True)
    options_price = fields.Monetary('Сума опцій', compute='_compute_options_price',
                                    store=True, currency_field='currency_id')
    total_price = fields.Monetary('Разом до сплати', compute='_compute_total_price',
                                  store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Валюта',
                                  default=lambda self: self.env.company.currency_id)

    # Контрагенти / документи
    supplier_id = fields.Many2one('res.partner', 'Постачальник',
                                  domain="[('supplier_rank', '>', 0)]")
    partner_id = fields.Many2one('res.partner', 'Покупець', tracking=True)
    sale_order_id = fields.Many2one('sale.order', 'Замовлення продажу', copy=False)
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', 'Авто клієнта (fleet)', copy=False,
                                       help='Створюється при видачі авто клієнту')

    location_note = fields.Char('Місце зберігання')
    note = fields.Text('Примітки')
    company_id = fields.Many2one('res.company', 'Компанія', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('vin_uniq', 'unique(vin)', 'Автомобіль з таким VIN вже існує на складі.'),
    ]

    @api.model
    def _expand_status(self, statuses, domain):
        return [s[0] for s in type(self).status.selection]

    @api.depends('model_id.brand_id.name', 'model_id.name', 'vin', 'color_id.name')
    def _compute_name(self):
        for car in self:
            parts = [car.model_id.brand_id.name or '', car.model_id.name or '']
            label = '/'.join(p for p in parts if p)
            if car.color_id:
                label = '%s (%s)' % (label, car.color_id.name)
            if car.vin:
                label = '%s — %s' % (label, car.vin)
            car.name = label or _('Новий автомобіль')

    @api.depends('option_ids.price')
    def _compute_options_price(self):
        for car in self:
            car.options_price = sum(car.option_ids.mapped('price'))

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
            raise UserError(_('Резервувати можна лише авто зі статусом «На складі».'))
        self._set_status('reserved')

    def action_unreserve(self):
        self._set_status('in_stock')

    def action_sell(self):
        """Продати авто (аналог РеализацияАвтомобилей)."""
        for car in self:
            if not car.partner_id:
                raise UserError(_('Вкажіть покупця перед продажем авто.'))
        self._set_status('sold')

    def action_deliver(self):
        """Видати авто клієнту і завести його як fleet.vehicle клієнта."""
        for car in self:
            if car.status != 'sold':
                raise UserError(_('Видати можна лише продане авто.'))
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

    @api.model
    def find_by_vin(self, vin):
        if not vin:
            return self.browse()
        return self.search([('vin', '=', vin.strip())], limit=1)

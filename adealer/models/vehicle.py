# -*- coding: utf-8 -*-

import os
import base64
from odoo import models, fields, api

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    name = fields.Char(compute="_compute_vehicle_name", store=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    volume = fields.Integer(string='Volume')
    photo = fields.Image(string='Vehicle Photo', max_width=512, max_height=512,
                         help="The vehicle's own photo (optional). If empty, the brand logo is shown.")
    brand_logo = fields.Image(related='model_id.brand_id.image_128', string='Brand Logo', readonly=True)
    display_logo = fields.Image(string='Logo', compute='_compute_display_logo')
    drive_type = fields.Selection([('4WD', '4WD'), ('AWD', 'AWD'), ('back', 'Back'), ('front', 'Front')], 'Drive Type', help='Drive type Used by the vehicle')
    transmission = fields.Selection(
        selection_add=[
            ('5MT', '5MT'), ('6MT', '6MT'),
            ('7AT', '7AT'), ('8AT', '8AT'), ('10AT', '10AT'),
        ],
        ondelete={
            '5MT': 'set null', '6MT': 'set null',
            '7AT': 'set null', '8AT': 'set null', '10AT': 'set null',
        },
        help='Transmission Used by the vehicle')
    body_type = fields.Many2one('vehicle.body', 'Vehicle Body')

    @api.depends('model_id.brand_id.name', 'model_id.name', 'vin_sn')
    def _compute_vehicle_name(self):
        for record in self:
            record.name = (record.model_id.brand_id.name or '') + '/' + (record.model_id.name or '')
            if record.vin_sn:
                record.name = record.name + '/' + (record.vin_sn or '')

    @api.depends('photo', 'brand_logo')
    def _compute_display_logo(self):
        use_brand = self.env['ir.config_parameter'].sudo().get_param(
            'adealer.brand_logo_default', 'True') in ('True', 'true', '1', True)
        for v in self:
            v.display_logo = v.photo or (v.brand_logo if use_brand else False)

    @api.model
    def find_by_vin(self, vin):
        """Пошук автомобіля за VIN (аналог 1С ПолучитьАвтомобильПоVIN)."""
        if not vin:
            return self.browse()
        return self.search([('vin_sn', '=', vin.strip())], limit=1)


class FleetVehicleModelBrand(models.Model):
    """Brand авто + вбудована база логотипів.

    Модуль постачається з набором фірмових логотипів популярних марок
    (static/img/brand_<назва>-image.png). При створенні марки її логотип
    підставляється автоматично за назвою; для наявних марок — кнопкою/хуком.
    """
    _inherit = 'fleet.vehicle.model.brand'

    @api.model_create_multi
    def create(self, vals_list):
        brands = super().create(vals_list)
        brands._apply_bundled_logo()
        return brands

    def _apply_bundled_logo(self):
        """Призначити логотип із вбудованої бази, якщо власного зображення ще немає."""
        img_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img')
        for brand in self:
            if brand.image_128 or not brand.name:
                continue
            slug = brand.name.strip().lower().replace(' ', '-')
            path = os.path.join(img_dir, 'brand_%s-image.png' % slug)
            if os.path.exists(path):
                with open(path, 'rb') as fh:
                    brand.image_128 = base64.b64encode(fh.read())

    @api.model
    def action_load_bundled_logos(self):
        """Призначити логотипи всім маркам без зображення (з вбудованої бази)."""
        self.search([]).filtered(lambda b: not b.image_128)._apply_bundled_logo()
        return True


class BodyType(models.Model):
    _name = 'vehicle.body'
    _description = 'Vehicle Body Type'

    name = fields.Char()
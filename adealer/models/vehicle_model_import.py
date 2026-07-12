import pandas as pd
import os
from odoo import models, api, _
from odoo.exceptions import UserError

def safe_val(val, cast_func=None):
    if val is None:
        return False
    if isinstance(val, float) and pd.isna(val):
        return False
    if isinstance(val, str) and not val.strip():
        return False
    if cast_func:
        try:
            return cast_func(val)
        except Exception:
            return False
    return val

class FleetVehicleModelImport(models.TransientModel):
    _name = 'fleet.vehicle.model.import'
    _description = 'Імпорт моделей авто з Excel'

    @api.model
    def import_vehicle_models_from_excel(self):
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'import_vehicle_models.xlsx')
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise UserError(_('Не вдалося відкрити файл: %s') % e)

        # Бренд за замовчуванням (налаштовується параметром adealer.import_default_brand)
        brand_name = self.env['ir.config_parameter'].sudo().get_param('adealer.import_default_brand', 'Auto')
        brand = self.env['fleet.vehicle.model.brand'].search([('name', '=', brand_name)], limit=1)
        if not brand:
            brand = self.env['fleet.vehicle.model.brand'].create({'name': brand_name})

        for idx, row in df.iterrows():
            model_name = safe_val(row.get('Найменування'))
            if not model_name:
                continue

            if self.env['fleet.vehicle.model'].search([('name', '=', model_name), ('brand_id', '=', brand.id)], limit=1):
                continue

            self.env['fleet.vehicle.model'].create({
                'name': model_name,
                'brand_id': brand.id,
            })
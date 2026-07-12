import pandas as pd
import math
import os
from datetime import datetime
from odoo import models, api, _
from odoo.exceptions import UserError

def safe_val(val, cast_func=None):
    if val is None:
        return False
    if isinstance(val, float) and math.isnan(val):
        return False
    if isinstance(val, str) and not val.strip():
        return False
    if cast_func:
        try:
            return cast_func(val)
        except Exception:
            return False
    return val


def parse_1c_date(val):
    """Розбір дати 1С ('ДД.ММ.РРРР'). Повертає date або False.
    Відсіює биті значення (напр. рік 0207), щоб не смітити в базі."""
    s = safe_val(val)
    if not s:
        return False
    s = str(s).strip()
    for fmt in ('%d.%m.%Y', '%d.%m.%y'):
        try:
            d = datetime.strptime(s, fmt).date()
        except ValueError:
            continue
        if 1950 <= d.year <= datetime.today().year:
            return d
        return False
    return False

class FleetVehicleImport(models.TransientModel):
    _name = 'fleet.vehicle.import'
    _description = 'Import vehicles from Excel'

    @api.model
    def import_vehicles_from_excel(self):
        # Вкажіть шлях до файлу Excel
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'import_vehicles.xlsx')
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise UserError(_('Could not open the file: %s') % e)

        for idx, row in df.iterrows():
            # Обробка transmission
            transmission_raw = str(safe_val(row.get('КПП'), str)).lower()
            if 'механ' in transmission_raw:
                transmission = 'manual'
            elif 'автомат' in transmission_raw:
                transmission = 'automatic'
            else:
                transmission = False

            # Обробка drive_type
            drive_type_raw = str(safe_val(row.get('Тип привода'), str)).lower()
            if 'перед' in drive_type_raw or 'fwd' in drive_type_raw:
                drive_type = 'front'
            elif 'зад' in drive_type_raw or 'rwd' in drive_type_raw:
                drive_type = 'back'
            elif 'awd' in drive_type_raw:
                drive_type = 'AWD'
            elif '4wd' in drive_type_raw:
                drive_type = '4WD'
            else:
                drive_type = False

            year = safe_val(row.get('Год выпуска'), int)
            vin_sn = safe_val(row.get('Вин код'))
            model_name = safe_val(row.get('Модель'))
            license_plate = safe_val(row.get('Гос номер'))
            client_name = safe_val(row.get('Клиент'))
            notes = safe_val(row.get('Примечание'))
            engine = safe_val(row.get('Двигатель'), int)
            body_type_name = safe_val(row.get('Тип кузова'))
            sale_date = parse_1c_date(row.get('Дата продажи'))

            model = self.env['fleet.vehicle.model'].search([('name', '=', model_name)], limit=1)
            if not model_name or not model:
                # Пропустити рядок, якщо не вказано назву моделі або не вдалося створити модель
                continue

            vals = {
                'model_id': model.id,
                'license_plate': license_plate,
                'vin_sn': vin_sn,
                'driver_id': self.env['res.partner'].search([('name', '=', client_name)], limit=1).id if client_name else False,
                'name': model_name,
                # 'notes': notes,
                'odometer': False,  # якщо є пробіг, додайте сюди
                # Дата продажу з 1С -> дата придбання. Якщо дати немає -
                # явний False, щоб НЕ спрацював дефолт (сьогодні).
                'acquisition_date': sale_date,
                # 'year': year,
                'volume': engine,
                'transmission': transmission,
                'body_type': self.env['vehicle.body'].search([('name', '=', body_type_name)], limit=1).id if body_type_name else False,
                'drive_type': drive_type,
            }
            # Уникати дублювання по VIN
            if vals.get('vin_sn') and self.env['fleet.vehicle'].search([('vin_sn', '=', vals['vin_sn'])], limit=1):
                continue

            self.env['fleet.vehicle'].create(vals)
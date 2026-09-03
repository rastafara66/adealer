# -*- coding: utf-8 -*-

from . import error_report  # декоратор report_errors + модель звітів (перший — його імпортують інші)
from . import addresses_import
from . import addresses_import_wizard
from . import maintenance
from . import partner_child_cleanup_wizard
from . import partner_import
from . import partner
from . import partner_import_wizard
from . import product
from . import res_config_settings
from . import res_users
from . import sale
from . import service
from . import service_request
from . import document_chain
from . import stock
from . import ir_http
from . import vehicle_import
from . import vehicle_model_import
from . import vehicle
from . import report_wizards
# --- Alfa-фічі (Альфа-Авто): нормо-години, стадії наряду, аналоги ЗЧ,
#     склад авто (VIN), сервісні кампанії, виробіток механіків ---
from . import normo_hours
from . import mechanic_report
from . import repair_stage
from . import part_analog
from . import dealer_car
from . import car_image
from . import service_campaign
from . import vehicle_service
from . import report_helpers
from . import app_update
from . import organization
from . import dashboard
from . import service_booking
# Підказки про платні надбудови. Останнім: домішує міксин у моделі вище.
from . import addon_hint

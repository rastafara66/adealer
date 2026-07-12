# -*- coding: utf-8 -*-
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        res = super().session_info()
        try:
            val = self.env['ir.config_parameter'].sudo().get_param('adealer.sidebar_enabled', 'True')
            res['adealer_sidebar_enabled'] = val in ('True', 'true', '1')
        except Exception:
            res['adealer_sidebar_enabled'] = False
        return res

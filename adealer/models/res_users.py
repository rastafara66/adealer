# -*- coding: utf-8 -*-
from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.depends('create_date')
    def _compute_tour_enabled(self):
        """Ніколи не вмикати онбординг-тури (ті «краплі»/підказки).
        Перекриває web_tour, який вмикає тури для адміна без demo-модулів."""
        for user in self:
            user.tour_enabled = False

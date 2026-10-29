# -*- coding: utf-8 -*-
from odoo import models, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.depends('create_date')
    def _compute_tour_enabled(self):
        """Ніколи не вмикати онбординг-тури (ті «краплі»/підказки).
        Перекриває web_tour, який вмикає тури для адміна без demo-модулів.
        Діє лише на нових користувачів — наявних вимикає _adealer_tours_off."""
        for user in self:
            user.tour_enabled = False

    @api.model
    def switch_tour_enabled(self, val):
        """Тур, запущений вручну (кнопка, ?tour=, пункт «Onboarding» меню
        налагодження), вмикав тури всьому користувачу знову — не вмикаємо."""
        self.env.user.sudo().tour_enabled = False
        return False

    @api.model
    def _adealer_tours_off(self):
        """При встановленні й кожному оновленні модуля (data/tours_off.xml):
        тури вимкнено всім, хто вже є в базі, — зокрема адміну, створеному
        разом із базою до встановлення 3A-dealer."""
        self.sudo().with_context(active_test=False).search(
            [('tour_enabled', '=', True)]).write({'tour_enabled': False})

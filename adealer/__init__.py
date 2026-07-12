# -*- coding: utf-8 -*-

from . import controllers
from . import models


def post_init_hook(env):
    """Призначити вбудовані логотипи наявним маркам авто при встановленні."""
    env['fleet.vehicle.model.brand'].search([])._apply_bundled_logo()
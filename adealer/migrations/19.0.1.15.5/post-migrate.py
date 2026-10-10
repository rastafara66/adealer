# -*- coding: utf-8 -*-
"""Group names and the category description were Ukrainian source text.

Until 19.0.1.15.4 the access groups were called «Користувач» and «Керівник»
in the XML itself, so an administrator with an English, French or German
interface saw Ukrainian. The XML now says User / Manager and the Ukrainian
comes from the translation, like every other label.

The records are ``noupdate``: an upgrade does not touch them, so a database
installed earlier would keep the Ukrainian names forever. This renames them
once, and only while the stored English value is still the old Ukrainian
text -- a name someone changed by hand is left alone.
"""
import re

from odoo import SUPERUSER_ID, api

CYRILLIC = re.compile('[Ѐ-ӿ]')

NEW = {
    'adealer.group_adealer_user': {
        'name': 'User',
        'comment': 'Daily work: repair orders, service bookings, customer vehicles, '
                   'vehicle stock, campaigns. No reference data and no settings.',
    },
    'adealer.group_adealer_manager': {
        'name': 'Manager',
        'comment': 'Everything a user can do, plus reference data, settings, imports '
                   'and settlement reports.',
    },
    'adealer.module_category_adealer': {
        'description': 'Car dealership, workshop, parts',
    },
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {'lang': 'en_US'})
    for xmlid, values in NEW.items():
        record = env.ref(xmlid, raise_if_not_found=False)
        if not record:
            continue
        stale = {field: text for field, text in values.items()
                 if CYRILLIC.search(record[field] or '')}
        if stale:
            record.write(stale)

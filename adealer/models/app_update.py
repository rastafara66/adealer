# -*- coding: utf-8 -*-
"""Application updates: check the latest published version and (optionally)
update the module from its git checkout.

- Version check: an HTTP GET to a configurable URL (default: the raw
  __manifest__.py on GitHub). Runs weekly via cron and on demand from
  Settings. Nothing is downloaded or executed automatically.
- "Update from GitHub": explicit admin action; works only when the module
  directory is a git checkout. Does `git pull --ff-only`, then upgrades the
  module. A server restart is still needed to reload changed Python code.
"""
import logging
import os
import re
import subprocess

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.modules.module import get_module_path

from .error_report import report_errors

_logger = logging.getLogger(__name__)

DEFAULT_CHANNEL_URL = (
    'https://raw.githubusercontent.com/rastafara66/adealer/19.0/adealer/__manifest__.py')
VERSION_RE = re.compile(r"""['"]version['"]\s*:\s*['"]([\d.]+)['"]""")


def _version_tuple(v):
    try:
        return tuple(int(x) for x in (v or '').split('.'))
    except ValueError:
        return ()


class AdealerAppUpdate(models.TransientModel):
    _name = 'adealer.app.update'
    _description = 'Application update helper'

    @api.model
    def _channel_url(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'adealer.update_channel_url', DEFAULT_CHANNEL_URL)

    @api.model
    def installed_version(self):
        mod = self.env['ir.module.module'].sudo().search([('name', '=', 'adealer')], limit=1)
        return mod.latest_version or ''

    @api.model
    def check_latest(self):
        """Fetch the latest published version and cache it. Returns (latest, available)."""
        url = self._channel_url()
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise UserError(_("Could not check for updates:\n%s") % e)
        m = VERSION_RE.search(resp.text)
        latest = m.group(1) if m else ''
        if not latest:
            raise UserError(_("Could not find a version number at the update URL."))
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('adealer.latest_version', latest)
        ICP.set_param('adealer.latest_checked', fields.Datetime.to_string(fields.Datetime.now()))
        available = _version_tuple(latest) > _version_tuple(self.installed_version())
        return latest, available

    @api.model
    @report_errors('cron_check_update')
    def _cron_check_update(self):
        """Weekly check; only logs and caches the result (shown in Settings)."""
        try:
            latest, available = self.check_latest()
        except UserError as e:
            _logger.warning("adealer update check failed: %s", e)
            return
        if available:
            _logger.warning("adealer: a newer version %s is available (installed %s)",
                            latest, self.installed_version())

    @api.model
    @report_errors('update_from_git')
    def update_from_git(self):
        """git pull --ff-only in the module checkout, then upgrade the module."""
        path = get_module_path('adealer')
        real = os.path.realpath(path)
        try:
            probe = subprocess.run(
                ['git', '-C', real, 'rev-parse', '--is-inside-work-tree'],
                capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as e:
            raise UserError(_("git is not available on the server:\n%s") % e)
        if probe.returncode != 0 or probe.stdout.strip() != 'true':
            raise UserError(_(
                "The module directory is not a git checkout (%s).\n"
                "Download the new version from the Odoo App Store instead.") % real)
        pull = subprocess.run(['git', '-C', real, 'pull', '--ff-only'],
                              capture_output=True, text=True, timeout=120)
        if pull.returncode != 0:
            raise UserError(_("git pull failed:\n%s") % (pull.stderr or pull.stdout))
        result = (pull.stdout or '').strip()
        self.env['ir.module.module'].sudo().search(
            [('name', '=', 'adealer')], limit=1).button_immediate_upgrade()
        return result


class ResConfigSettingsUpdate(models.TransientModel):
    _inherit = 'res.config.settings'

    adealer_version_installed = fields.Char("Installed version", readonly=True)
    adealer_version_latest = fields.Char("Latest published version", readonly=True)
    adealer_version_checked = fields.Char("Last checked", readonly=True)
    adealer_update_available = fields.Boolean("Update available", readonly=True)
    adealer_update_channel_url = fields.Char(
        "Update check URL",
        help="URL used to read the latest published version "
             "(a raw __manifest__.py or a text containing 'version': 'x.y.z').")

    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        upd = self.env['adealer.app.update']
        installed = upd.installed_version()
        latest = ICP.get_param('adealer.latest_version', '')
        res.update({
            'adealer_version_installed': installed,
            'adealer_version_latest': latest or _('(not checked yet)'),
            'adealer_version_checked': ICP.get_param('adealer.latest_checked', ''),
            'adealer_update_available': _version_tuple(latest) > _version_tuple(installed),
            'adealer_update_channel_url': ICP.get_param(
                'adealer.update_channel_url', DEFAULT_CHANNEL_URL),
        })
        return res

    def set_values(self):
        super().set_values()
        if self.adealer_update_channel_url:
            self.env['ir.config_parameter'].sudo().set_param(
                'adealer.update_channel_url', self.adealer_update_channel_url)

    def action_adealer_check_update(self):
        latest, available = self.env['adealer.app.update'].check_latest()
        msg = (_("A newer version %s is available.") % latest) if available \
            else (_("You are up to date (version %s).") % self.env['adealer.app.update'].installed_version())
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Application update"),
                'message': msg,
                'type': 'warning' if available else 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_adealer_update_from_git(self):
        result = self.env['adealer.app.update'].update_from_git()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Application update"),
                'message': _("Code updated (%s). The module was upgraded. "
                             "Restart the Odoo server to load changed Python code.") % (result or 'git'),
                'type': 'success',
                'sticky': True,
            },
        }

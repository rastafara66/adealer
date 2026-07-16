# -*- coding: utf-8 -*-
"""Organizations — a lightweight legal-entity dimension inside a single company.

Many dealers operate several legal entities (a company + one or more sole
proprietors) as one operational business. Instead of Odoo multi-company
(heavy for day-to-day managers), we keep a single company and tag every
document with an ``organization_id``. It defaults to the organization marked
as default, so users normally do not touch it.

Generic feature — part of the shared engine, not client-specific.
"""
from odoo import models, fields, api


class DealerOrganization(models.Model):
    _name = 'dealer.organization'
    _description = 'Organization'
    _order = 'is_default desc, name'

    name = fields.Char('Name', required=True)
    full_name = fields.Char('Full name')
    edrpou = fields.Char('EDRPOU', help='State registry code (ЄДРПОУ)')
    vat_code = fields.Char('Tax ID', help='Individual tax number (ІПН)')
    is_vat_payer = fields.Boolean('VAT payer')
    vat_certificate = fields.Char('VAT certificate No.')
    prefix = fields.Char('Document prefix')
    is_default = fields.Boolean('Default organization')
    active = fields.Boolean(default=True)

    @api.model
    def _default_org(self):
        """The organization put on new documents by default.

        Guard against install/upgrade time: when Odoo adds the
        ``organization_id`` column to an existing model and fills the default
        for the existing rows, this default runs while the
        ``dealer_organization`` table may not be created yet. Without the guard
        the upgrade from a version without this feature crashes with
        ``relation "dealer_organization" does not exist`` and rolls back.
        """
        self.env.cr.execute("SELECT to_regclass('dealer_organization')")
        if not self.env.cr.fetchone()[0]:
            return self.browse()
        org = self.search([('is_default', '=', True)], limit=1)
        if not org:
            org = self.search([], limit=1)
        return org

    def _ensure_single_default(self):
        default = self.filtered('is_default')
        if default:
            others = self.search([('is_default', '=', True),
                                  ('id', 'not in', default.ids)])
            if others:
                others.with_context(skip_default_check=True).write({'is_default': False})

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs._ensure_single_default()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_default') and not self.env.context.get('skip_default_check'):
            self._ensure_single_default()
        return res


class DealerOrganizationMixin(models.AbstractModel):
    """Adds ``organization_id`` (defaulting to the default org) to a document."""
    _name = 'dealer.organization.mixin'
    _description = 'Organization mixin'

    organization_id = fields.Many2one(
        'dealer.organization', string='Organization', index=True,
        default=lambda self: self.env['dealer.organization']._default_org())


class SaleOrderOrg(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'dealer.organization.mixin']


class PurchaseOrderOrg(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'dealer.organization.mixin']


class AccountMoveOrg(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'dealer.organization.mixin']


class AccountPaymentOrg(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'dealer.organization.mixin']


class RepairOrderOrg(models.Model):
    _name = 'repair.order'
    _inherit = ['repair.order', 'dealer.organization.mixin']


class StockPickingOrg(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'dealer.organization.mixin']

# -*- coding: utf-8 -*-
"""Service request — the entry point of the service workflow.

Why a separate model. The booking that a customer makes by phone is not yet a
sale order: there is no agreed scope, no prices, often no confirmed vehicle.
Until now the "Maintenance requests" menu opened plain sale orders, so a call
could only be recorded by creating a real order — and the workshop calendar had
to be built on repair orders, which appear even later in the chain.

Document chain:

    Service request  ->  Sale order  ->  Repair order  ->  Delivery note

The request keeps only what is known when the phone rings: when, who, which
car, what they complain about. The scope and money start with the sale order.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ServiceRequest(models.Model):
    _name = 'adealer.service.request'
    _description = 'Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc, id desc'

    name = fields.Char(
        string='Number', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True)
    scheduled_date = fields.Datetime(
        string='Scheduled', required=True, index=True,
        default=fields.Datetime.now,
        help='When the customer is expected at the workshop')
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, index=True,
        tracking=True)
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string='Vehicle', index=True, tracking=True)
    vehicle_logo = fields.Image(
        related='vehicle_id.display_logo', string='Vehicle Logo', readonly=True)
    mileage = fields.Float(
        string='Mileage', help='Vehicle mileage stated by the customer')
    reason = fields.Text(
        string='Reason', help='What the customer complains about, in their own words')
    service_advisor_id = fields.Many2one(
        'res.users', string='Manager', default=lambda self: self.env.user,
        tracking=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('confirmed', 'Confirmed'),
        ('done', 'Order created'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order', copy=False, readonly=True,
        help='The order created from this request')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    note = fields.Text(string='Internal note')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'adealer.service.request') or '/'
        return super().create(vals_list)

    @api.depends('name')
    def _compute_display_name(self):
        """Name the document kind in breadcrumbs and m2o fields,
        same rationale as repair.order and sale.order in this module."""
        for req in self:
            req.display_name = _("Service request No. %s") % (req.name or '/')

    # Дії-кнопки повертають True, а не None: XML-RPC-сервер маршалить
    # відповідь із allow_none=False і на None падає (перевірено дим-тестом).
    def action_confirm(self):
        for req in self:
            if req.state != 'draft':
                raise UserError(_('Only a new request can be confirmed.'))
            req.state = 'confirmed'
        return True

    def action_cancel(self):
        for req in self:
            if req.sale_order_id:
                raise UserError(_(
                    'The request already has order %s. Cancel the order first.')
                    % req.sale_order_id.name)
            req.state = 'cancel'
        return True

    def action_draft(self):
        self.write({'state': 'draft'})
        return True

    def action_create_sale_order(self):
        """Create the customer order this request turns into.

        One request produces one order: a second click would silently double
        the workload for the workshop, so it is refused rather than allowed."""
        self.ensure_one()
        if self.sale_order_id:
            raise UserError(_('Order %s has already been created from this request.')
                            % self.sale_order_id.name)
        if self.state == 'cancel':
            raise UserError(_('The request is cancelled.'))
        order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'vehicle_id': self.vehicle_id.id,
            'origin': self.name,
        })
        self.write({'sale_order_id': order.id, 'state': 'done'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

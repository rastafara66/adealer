# -*- coding: utf-8 -*-
"""Ланцюжок документів «ввод на підставі» від наряду (repair.order):
- Рахунок (проформа, товари+послуги) — account.move, чернетка (без проводок).
- Видаткова (товари) — account.move, проводить дохід по товарах.
- Акт виконаних робіт (послуги) — account.move, проводить дохід по послугах.
- Видати ЗЧ зі складу — stock.picking (відвантаження, «кладовщик видає»).
Кожен документ тримає посилання на наряд-джерело (subordination).
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    source_repair_order_id = fields.Many2one(
        'repair.order', string='Наряд-джерело', copy=False, index=True,
        help='Наряд-Заказ, на підставі якого створено цей документ')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    source_repair_order_id = fields.Many2one(
        'repair.order', string='Наряд-джерело', copy=False, index=True)


class RepairOrderChain(models.Model):
    _inherit = 'repair.order'

    invoice_ids = fields.One2many(
        'account.move', 'source_repair_order_id', string='Рахунки/Видаткові/Акти')
    invoice_count = fields.Integer(compute='_compute_chain_counts')
    picking_ids = fields.One2many(
        'stock.picking', 'source_repair_order_id', string='Відвантаження')
    picking_count = fields.Integer(compute='_compute_chain_counts')

    @api.depends('invoice_ids', 'picking_ids')
    def _compute_chain_counts(self):
        for order in self:
            order.invoice_count = len(order.invoice_ids)
            order.picking_count = len(order.picking_ids)

    # ---------- рахунки / видаткові / акти (account.move) ----------
    def _chain_invoice_lines(self, mode):
        """mode: 'goods' | 'services' | 'all'."""
        self.ensure_one()
        lines = []
        for op in self.operations:
            if not op.product_id:
                continue
            is_service = op.product_id.type == 'service'
            if mode == 'goods' and is_service:
                continue
            if mode == 'services' and not is_service:
                continue
            lines.append((0, 0, {
                'product_id': op.product_id.id,
                'quantity': op.product_uom_qty,
                'price_unit': op.price_unit,
                'tax_ids': [(6, 0, op.tax_id.ids)],
            }))
        return lines

    def _build_chain_move(self, mode, label, post=False, silent=False):
        """Створити account.move (out_invoice) на підставі наряду.
        silent=True — не кидати помилку, якщо немає рядків (для авто-проведення).
        post=True — одразу провести. Повертає move (або порожній, якщо silent і нема рядків)."""
        self.ensure_one()
        if not self.partner_id:
            if silent:
                return self.env['account.move']
            raise UserError(_("У наряді %s не вказано клієнта.") % self.name)
        lines = self._chain_invoice_lines(mode)
        if not lines:
            if silent:
                return self.env['account.move']
            raise UserError(
                _("У наряді %(name)s немає рядків для документа «%(label)s».") % {
                    'name': self.name, 'label': label})
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'ref': '%s %s' % (label, self.name),
            'source_repair_order_id': self.id,
            'invoice_line_ids': lines,
        })
        if post:
            move.action_post()
        return move

    def _create_chain_invoice(self, mode, label):
        move = self._build_chain_move(mode, label)
        return {
            'type': 'ir.actions.act_window',
            'name': label,
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
        }

    def action_create_rakhunok(self):
        """Рахунок (проформа, товари+послуги) — лишається чернеткою."""
        return self._create_chain_invoice('all', _("Рахунок"))

    def action_create_vydatkova(self):
        """Видаткова (товари) — проводить дохід по товарах."""
        return self._create_chain_invoice('goods', _("Видаткова"))

    def action_create_akt(self):
        """Акт виконаних робіт (послуги) — проводить дохід по послугах."""
        return self._create_chain_invoice('services', _("Акт"))

    def action_view_invoices(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Рахунки/Видаткові/Акти'),
            'res_model': 'account.move',
            'domain': [('source_repair_order_id', '=', self.id)],
        }
        if self.invoice_count == 1:
            action.update(view_mode='form', res_id=self.invoice_ids.id)
        else:
            action.update(view_mode='list,form')
        return action

    # ---------- видача ЗЧ у цех: внутрішнє переміщення (для нового наряду) ----------
    def _service_location(self, warehouse):
        """Внутрішня локація «Ремонтна зона (СТО)» для видачі ЗЧ у цех.
        Створюється за потреби (аналог 1С внутрішнього переміщення в цех)."""
        Loc = self.env['stock.location']
        loc = Loc.search([('name', '=', 'Ремонтна зона (СТО)'),
                          ('location_id', '=', warehouse.view_location_id.id)], limit=1)
        if not loc:
            loc = Loc.create({
                'name': 'Ремонтна зона (СТО)',
                'usage': 'internal',
                'location_id': warehouse.view_location_id.id,
                'company_id': warehouse.company_id.id,
            })
        return loc

    def _issue_parts_picking(self):
        """Внутрішнє переміщення складських ЗЧ наряду зі складу в ремонтну зону
        (створюється і проводиться для нового наряду). Повертає picking або False."""
        self.ensure_one()
        goods = self.operations.filtered(
            lambda o: o.product_id and o.product_id.type != 'service' and o.product_id.is_storable)
        if not goods:
            return False
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id)], limit=1)
        if not warehouse:
            raise UserError(_("Не знайдено склад для компанії."))
        ptype = warehouse.int_type_id or self.env['stock.picking.type'].search(
            [('code', '=', 'internal'), ('warehouse_id', '=', warehouse.id)], limit=1)
        if not ptype:
            raise UserError(_("Не налаштовано тип «Внутрішнє переміщення» на складі."))
        src = warehouse.lot_stock_id
        dest = self._service_location(warehouse)
        moves = []
        for op in goods:
            uom = op.product_uom or op.product_id.uom_id
            moves.append((0, 0, {
                'product_id': op.product_id.id,
                'product_uom_qty': op.product_uom_qty,
                'product_uom': uom.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
            }))
        picking = self.env['stock.picking'].create({
            'picking_type_id': ptype.id,
            'origin': self.name,
            'source_repair_order_id': self.id,
            'location_id': src.id,
            'location_dest_id': dest.id,
            'move_ids': moves,
        })
        picking.action_confirm()
        return picking

    def action_issue_parts(self):
        """Видати ЗЧ у цех (внутрішнє переміщення) — на підставі наряду."""
        self.ensure_one()
        picking = self._issue_parts_picking()
        if not picking:
            raise UserError(_("У наряді %s немає складських запчастин для видачі.") % self.name)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Видача ЗЧ у цех'),
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
        }

    # ---------- проведення наряду (Відремонтовано → авто віддали клієнту) ----------
    def _autopost_docs_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'adealer.autopost_repair_docs', 'False') in ('True', 'true', '1', True)

    def action_repair_end(self):
        """Проведення наряду (авто віддали клієнту): якщо в налаштуваннях увімкнено
        авто-режим — формуємо реалізацію: Акт (послуги) + Видаткова (товари)."""
        res = super().action_repair_end()
        if not self._autopost_docs_enabled():
            return res
        for order in self:
            if order.state != 'done' or order.invoice_ids:
                continue
            akt = order._build_chain_move('services', _("Акт"), post=True, silent=True)
            vyd = order._build_chain_move('goods', _("Видаткова"), post=True, silent=True)
            created = [m.name for m in (akt + vyd) if m]
            if created:
                order.message_post(body=_(
                    "Наряд проведено (реалізація клієнту): %s.") % ", ".join(created))
        return res

    def action_view_source_order(self):
        """Відкрити замовлення покупця, на підставі якого створено наряд."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Замовлення покупця'),
            'res_model': 'sale.order',
            'res_id': self.source_sale_order_id.id,
            'view_mode': 'form',
        }

    def action_view_pickings(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Відвантаження'),
            'res_model': 'stock.picking',
            'domain': [('source_repair_order_id', '=', self.id)],
        }
        if self.picking_count == 1:
            action.update(view_mode='form', res_id=self.picking_ids.id)
        else:
            action.update(view_mode='list,form')
        return action

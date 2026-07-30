# -*- coding: utf-8 -*-
"""Reports у класичному стилі: шапка параметрів (період, відбори) + кнопка «Generate»
+ таблична частина (відомість). Перший звіт — Receivables with counterparties."""
from odoo import models, fields, api, _


class PartnerBalanceWizard(models.TransientModel):
    _name = 'partner.balance.wizard'
    _description = 'Receivables with counterparties (statement)'

    date_from = fields.Date(
        'Period from', required=True,
        default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))
    date_to = fields.Date(
        'to', required=True,
        default=lambda self: fields.Date.context_today(self))
    partner_id = fields.Many2one(
        'res.partner', string='Counterparty',
        help='Empty — summary across all counterparties')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id.id)
    line_ids = fields.One2many(
        'partner.balance.wizard.line', 'wizard_id', string='Statement', readonly=True)

    def _aml_domain(self):
        return [('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
                ('parent_state', '=', 'posted')]

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        AML = self.env['account.move.line']
        Line = self.env['partner.balance.wizard.line']
        cur = self.env.company.currency_id.id
        seq = 0

        def add(vals):
            nonlocal seq
            seq += 1
            vals.update(wizard_id=self.id, sequence=seq, currency_id=cur)
            return Line.create(vals)

        if self.partner_id:
            pdom = [('partner_id', '=', self.partner_id.id)]
            opening = sum(AML.search(
                self._aml_domain() + pdom + [('date', '<', self.date_from)]).mapped('balance'))
            add({'line_type': 'opening', 'doc_name': _('Opening balance'),
                 'balance': opening})
            run = opening
            tdeb = tcred = 0.0
            moves = AML.search(
                self._aml_domain() + pdom +
                [('date', '>=', self.date_from), ('date', '<=', self.date_to)],
                order='date, id')
            for ml in moves:
                run += ml.balance
                tdeb += ml.debit
                tcred += ml.credit
                add({'line_type': 'move', 'date': ml.date,
                     'doc_name': ml.move_id.ref or ml.move_id.name,
                     'move_id': ml.move_id.id,
                     'debit': ml.debit, 'credit': ml.credit, 'balance': run})
            add({'line_type': 'total', 'doc_name': _('Turnover for the period'),
                 'debit': tdeb, 'credit': tcred})
            add({'line_type': 'closing', 'doc_name': _('Closing balance'),
                 'balance': run})
        else:
            # зведення to всіх контрагентах: залишок на початок / обороти / на кінець
            data = {}
            for ml in AML.search(self._aml_domain() + [('date', '<=', self.date_to)]):
                rec = data.setdefault(ml.partner_id, [0.0, 0.0, 0.0])
                if ml.date < self.date_from:
                    rec[0] += ml.balance
                else:
                    rec[1] += ml.debit
                    rec[2] += ml.credit
            g_open = g_deb = g_cred = g_close = 0.0
            for partner in sorted(data, key=lambda p: p.display_name or ''):
                opening, deb, cred = data[partner]
                closing = opening + deb - cred
                if not (opening or deb or cred):
                    continue
                g_open += opening
                g_deb += deb
                g_cred += cred
                g_close += closing
                add({'line_type': 'partner',
                     'doc_name': partner.display_name or _('No counterparty'),
                     'partner_line_id': partner.id or False,
                     'opening': opening, 'debit': deb, 'credit': cred,
                     'balance': closing})
            add({'line_type': 'total', 'doc_name': _('Total'),
                 'opening': g_open, 'debit': g_deb, 'credit': g_cred,
                 'balance': g_close})
        return True


class PartnerBalanceWizardLine(models.TransientModel):
    _name = 'partner.balance.wizard.line'
    _description = 'Receivables statement line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('partner.balance.wizard', required=True, ondelete='cascade')
    sequence = fields.Integer()
    line_type = fields.Selection([
        ('opening', 'Opening balance'),
        ('move', 'Document'),
        ('partner', 'Counterparty'),
        ('total', 'Turnover'),
        ('closing', 'Closing balance')])
    date = fields.Date('Date')
    doc_name = fields.Char('Document / Counterparty')
    move_id = fields.Many2one('account.move', string='Document')
    partner_line_id = fields.Many2one('res.partner', string='Counterparty')
    currency_id = fields.Many2one('res.currency')
    opening = fields.Monetary('Opening balance', currency_field='currency_id')
    debit = fields.Monetary('Debit (accrued)', currency_field='currency_id')
    credit = fields.Monetary('Credit (paid)', currency_field='currency_id')
    balance = fields.Monetary('On hand', currency_field='currency_id')

    def action_open_move(self):
        self.ensure_one()
        if not self.move_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }

    def action_open_partner(self):
        """Провалитись у деталізацію to контрагенту (як у 1С)."""
        self.ensure_one()
        if not self.partner_line_id:
            return False
        wiz = self.env['partner.balance.wizard'].create({
            'date_from': self.wizard_id.date_from,
            'date_to': self.wizard_id.date_to,
            'partner_id': self.partner_line_id.id,
        })
        wiz.action_generate()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receivables: %s') % self.partner_line_id.display_name,
            'res_model': 'partner.balance.wizard',
            'res_id': wiz.id,
            'view_mode': 'form',
            'target': 'current',
        }


REPAIR_STATES = {'draft': 'New', 'confirmed': 'Confirmed',
                 'under_repair': 'Under repair', 'done': 'Repaired',
                 'cancel': 'Cancelled'}
SALE_STATES = {'draft': 'Draft', 'sent': 'Sent', 'sale': 'Confirmed',
               'done': 'Done', 'cancel': 'Cancelled'}


class AdealerReportWizard(models.TransientModel):
    """Універсальний «готовий» звіт у класичному стилі: шапка параметрів + відомість.
    Один тип звіту = одна form-в'юха зі своїми колонками."""
    _name = 'adealer.report.wizard'
    _description = 'Ready report'

    report_type = fields.Selection([
        ('sales', 'Sales'),
        ('gross', 'Gross profit'),
        ('purchases', 'Purchases'),
        ('stock', 'Stock on hand'),
        ('repairs', 'Repair history'),
        ('advisors', 'Advisor output'),
        ('orders', 'Customer order analysis'),
        ('to_reminder', 'Maintenance reminders'),
        ('inactive', 'Inactive customers'),
        ('abc_sales', 'ABC analysis of sales'),
        ('abc_customers', 'ABC analysis of customers'),
        ('turnover', 'Stock turnover'),
    ], required=True, default='sales')
    date_from = fields.Date(
        'Period from', required=True,
        default=lambda self: fields.Date.context_today(self).replace(month=1, day=1))
    date_to = fields.Date(
        'to', required=True,
        default=lambda self: fields.Date.context_today(self))
    partner_id = fields.Many2one('res.partner', string='Counterparty')
    product_id = fields.Many2one('product.product', string='Product')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id.id)
    line_ids = fields.One2many(
        'adealer.report.wizard.line', 'wizard_id', string='Statement', readonly=True)

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        vals_list = getattr(self, '_gen_%s' % self.report_type)()
        cur = self.env.company.currency_id.id
        for seq, vals in enumerate(vals_list, start=1):
            vals.update(wizard_id=self.id, sequence=seq, currency_id=cur)
        self.env['adealer.report.wizard.line'].create(vals_list)
        return True

    # ---------- джерела даних ----------
    def _sale_move_lines(self):
        dom = [('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
               ('parent_state', '=', 'posted'),
               ('display_type', '=', 'product'),
               ('date', '>=', self.date_from), ('date', '<=', self.date_to)]
        if self.partner_id:
            dom.append(('partner_id', '=', self.partner_id.id))
        if self.product_id:
            dom.append(('product_id', '=', self.product_id.id))
        return self.env['account.move.line'].search(dom, order='date, id')

    def _gen_sales(self):
        rows, tqty, tsum = [], 0.0, 0.0
        for ml in self._sale_move_lines():
            sign = -1.0 if ml.move_id.move_type == 'out_refund' else 1.0
            qty = sign * ml.quantity
            amt = sign * ml.price_subtotal
            tqty += qty
            tsum += amt
            rows.append({'line_type': 'row', 'date': ml.date,
                         'name': ml.move_id.ref or ml.move_id.name,
                         'ref2': ml.partner_id.display_name or '',
                         'ref3': ml.product_id.display_name or '',
                         'qty': qty, 'amount': amt,
                         'res_model': 'account.move', 'res_id': ml.move_id.id})
        rows.append({'line_type': 'total', 'name': _('Total'),
                     'qty': tqty, 'amount': tsum})
        return rows

    def _gen_gross(self):
        agg = {}
        for ml in self._sale_move_lines():
            sign = -1.0 if ml.move_id.move_type == 'out_refund' else 1.0
            rec = agg.setdefault(ml.product_id, [0.0, 0.0])
            rec[0] += sign * ml.quantity
            rec[1] += sign * ml.price_subtotal
        rows = []
        tq = trev = tcost = 0.0
        for product, (qty, rev) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
            cost = (product.standard_price or 0.0) * qty
            rows.append({'line_type': 'row', 'name': product.display_name,
                         'qty': qty, 'amount': rev, 'amount2': cost,
                         'amount3': rev - cost,
                         'res_model': 'product.product', 'res_id': product.id})
            tq += qty
            trev += rev
            tcost += cost
        rows.append({'line_type': 'total', 'name': _('Total'), 'qty': tq,
                     'amount': trev, 'amount2': tcost, 'amount3': trev - tcost})
        return rows

    def _gen_purchases(self):
        dom = [('state', '!=', 'cancel'),
               ('date_order', '>=', self.date_from), ('date_order', '<=', self.date_to)]
        if self.partner_id:
            dom.append(('partner_id', '=', self.partner_id.id))
        rows, tsum = [], 0.0
        for po in self.env['purchase.order'].search(dom, order='date_order, id'):
            tsum += po.amount_total
            rows.append({'line_type': 'row', 'date': po.date_order,
                         'name': po.name, 'ref2': po.partner_id.display_name or '',
                         'ref3': po.partner_ref or '',
                         'amount': po.amount_total,
                         'res_model': 'purchase.order', 'res_id': po.id})
        rows.append({'line_type': 'total', 'name': _('Total'), 'amount': tsum})
        return rows

    def _gen_stock(self):
        dom = [('location_id.usage', '=', 'internal')]
        if self.product_id:
            dom.append(('product_id', '=', self.product_id.id))
        agg = {}
        for q in self.env['stock.quant'].search(dom):
            agg[q.product_id] = agg.get(q.product_id, 0.0) + q.quantity
        rows = []
        tq = tsum = 0.0
        items = sorted(agg.items(),
                       key=lambda kv: -(kv[1] * (kv[0].standard_price or 0.0)))
        for product, qty in items:
            if not qty:
                continue
            val = qty * (product.standard_price or 0.0)
            rows.append({'line_type': 'row', 'name': product.display_name,
                         'ref2': product.default_code or '', 'qty': qty,
                         'amount': val,
                         'res_model': 'product.product', 'res_id': product.id})
            tq += qty
            tsum += val
        rows.append({'line_type': 'total', 'name': _('Total'), 'qty': tq, 'amount': tsum})
        return rows

    def _repair_domain(self):
        dom = [('schedule_date', '>=', self.date_from),
               ('schedule_date', '<=', self.date_to)]
        if self.partner_id:
            dom.append(('partner_id', '=', self.partner_id.id))
        if self.vehicle_id:
            dom.append(('vehicle_id', '=', self.vehicle_id.id))
        return dom

    def _gen_repairs(self):
        rows, tsum = [], 0.0
        for ro in self.env['repair.order'].search(self._repair_domain(),
                                                  order='schedule_date, id'):
            tsum += ro.amount_total
            rows.append({'line_type': 'row', 'date': ro.schedule_date,
                         'name': ro.name, 'ref2': ro.partner_id.display_name or '',
                         'ref3': ro.vehicle_id.display_name or '',
                         'amount': ro.amount_total,
                         'state': REPAIR_STATES.get(ro.state, ro.state),
                         'res_model': 'repair.order', 'res_id': ro.id})
        rows.append({'line_type': 'total', 'name': _('Total'), 'amount': tsum})
        return rows

    def _gen_advisors(self):
        agg = {}
        for ro in self.env['repair.order'].search(self._repair_domain()):
            key = ro.service_advisor_id or ro.user_id
            rec = agg.setdefault(key, [0, 0.0])
            rec[0] += 1
            rec[1] += ro.amount_total
        rows = []
        tn = tsum = 0
        for user, (cnt, total) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
            rows.append({'line_type': 'row',
                         'name': user.display_name if user else _('Not set'),
                         'qty': cnt, 'amount': total})
            tn += cnt
            tsum += total
        rows.append({'line_type': 'total', 'name': _('Total'), 'qty': tn, 'amount': tsum})
        return rows

    def _gen_orders(self):
        dom = [('date_order', '>=', self.date_from), ('date_order', '<=', self.date_to)]
        if self.partner_id:
            dom.append(('partner_id', '=', self.partner_id.id))
        if self.vehicle_id:
            dom.append(('vehicle_id', '=', self.vehicle_id.id))
        rows, tsum = [], 0.0
        for so in self.env['sale.order'].search(dom, order='date_order, id'):
            tsum += so.amount_total
            rows.append({'line_type': 'row', 'date': so.date_order,
                         'name': so.name, 'ref2': so.partner_id.display_name or '',
                         'ref3': so.vehicle_id.display_name or '',
                         'amount': so.amount_total,
                         'state': SALE_STATES.get(so.state, so.state),
                         'res_model': 'sale.order', 'res_id': so.id})
        rows.append({'line_type': 'total', 'name': _('Total'), 'amount': tsum})
        return rows


    # ---------- авто-звіти (аналог 1С) ----------
    def _gen_to_reminder(self):
        """Авто, що не були на ТО з дати «No service since» (НапоминаниеО_ТО)."""
        last = {}
        for ro in self.env['repair.order'].search([('vehicle_id', '!=', False)],
                                                  order='schedule_date'):
            last[ro.vehicle_id] = ro  # asc-порядок => лишиться останній візит
        today = fields.Date.context_today(self)
        items = [(v, ro) for v, ro in last.items()
                 if ro.schedule_date and ro.schedule_date.date() < self.date_from]
        items.sort(key=lambda t: t[1].schedule_date)
        rows = []
        for v, ro in items:
            days = (today - ro.schedule_date.date()).days
            rows.append({'line_type': 'row', 'date': ro.schedule_date,
                         'name': v.display_name,
                         'ref2': ro.partner_id.display_name or '',
                         'ref3': _('%d days ago') % days,
                         'qty': ro.mileage or 0.0,
                         'res_model': 'fleet.vehicle', 'res_id': v.id})
        rows.append({'line_type': 'total', 'name': _('Total'),
                     'ref3': _('vehicles: %d') % len(items)})
        return rows

    def _gen_inactive(self):
        """Клієнти, що не заїжджали з дати (НеЗаезжавшиеКлиенты)."""
        agg = {}
        for ro in self.env['repair.order'].search([('partner_id', '!=', False)]):
            rec = agg.setdefault(ro.partner_id, [None, 0, 0.0])
            rec[1] += 1
            rec[2] += ro.amount_total
            if not rec[0] or (ro.schedule_date and ro.schedule_date > rec[0]):
                rec[0] = ro.schedule_date
        today = fields.Date.context_today(self)
        items = [(p, r) for p, r in agg.items()
                 if r[0] and r[0].date() < self.date_from]
        items.sort(key=lambda t: t[1][0])
        rows = []
        for p, (dt, cnt, tot) in items:
            rows.append({'line_type': 'row', 'date': dt, 'name': p.display_name,
                         'ref3': _('%d days ago') % (today - dt.date()).days,
                         'qty': cnt, 'amount': tot,
                         'res_model': 'res.partner', 'res_id': p.id})
        rows.append({'line_type': 'total', 'name': _('Total'),
                     'ref3': _('customers: %d') % len(items),
                     'amount': sum(r[1][2] for r in items)})
        return rows

    def _abc_rows(self, agg, res_model):
        """agg: {record: (qty, amount)} -> ABC-рядки (A 80% / B 95% / C)."""
        items = sorted(agg.items(), key=lambda kv: -kv[1][1])
        total = sum(a for _q, a in agg.values()) or 1.0
        rows, cum = [], 0.0
        counts = {'A': 0, 'B': 0, 'C': 0}
        for rec, (qty, amt) in items:
            cum += amt
            klass = 'A' if cum <= total * 0.80 else ('B' if cum <= total * 0.95 else 'C')
            counts[klass] += 1
            rows.append({'line_type': 'row', 'name': rec.display_name,
                         'qty': qty, 'amount': amt,
                         'ref3': '%.1f%%' % (amt / total * 100.0),
                         'state': klass,
                         'res_model': res_model, 'res_id': rec.id})
        rows.append({'line_type': 'total', 'name': _('Total'),
                     'amount': sum(a for _q, a in agg.values()),
                     'ref3': 'A:%d B:%d C:%d' % (counts['A'], counts['B'], counts['C'])})
        return rows

    def _gen_abc_sales(self):
        agg = {}
        for ml in self._sale_move_lines():
            sign = -1.0 if ml.move_id.move_type == 'out_refund' else 1.0
            rec = agg.setdefault(ml.product_id, [0.0, 0.0])
            rec[0] += sign * ml.quantity
            rec[1] += sign * ml.price_subtotal
        return self._abc_rows({k: tuple(v) for k, v in agg.items()}, 'product.product')

    def _gen_abc_customers(self):
        agg = {}
        for ml in self._sale_move_lines():
            sign = -1.0 if ml.move_id.move_type == 'out_refund' else 1.0
            rec = agg.setdefault(ml.partner_id, [0.0, 0.0])
            rec[0] += 1
            rec[1] += sign * ml.price_subtotal
        return self._abc_rows({k: tuple(v) for k, v in agg.items()}, 'res.partner')

    def _gen_turnover(self):
        """Sold for the period vs поточний залишок; днів запасу."""
        period_days = max((self.date_to - self.date_from).days, 1)
        sold = {}
        for ml in self._sale_move_lines():
            sign = -1.0 if ml.move_id.move_type == 'out_refund' else 1.0
            sold[ml.product_id] = sold.get(ml.product_id, 0.0) + sign * ml.quantity
        onhand = {}
        for qn in self.env['stock.quant'].search([('location_id.usage', '=', 'internal')]):
            onhand[qn.product_id] = onhand.get(qn.product_id, 0.0) + qn.quantity
        rows = []
        tsold = 0.0
        for product, q in sorted(sold.items(), key=lambda kv: -kv[1]):
            if q <= 0:
                continue
            oh = onhand.get(product, 0.0)
            days = int(oh / (q / period_days)) if q > 0 else 0
            rows.append({'line_type': 'row', 'name': product.display_name,
                         'ref2': product.default_code or '',
                         'qty': q,
                         'ref3': _('on hand %(oh).0f pcs · %(days)d d.') % {'oh': oh, 'days': days},
                         'res_model': 'product.product', 'res_id': product.id})
            tsold += q
        rows.append({'line_type': 'total', 'name': _('Total'), 'qty': tsold})
        return rows


class AdealerReportWizardLine(models.TransientModel):
    _name = 'adealer.report.wizard.line'
    _description = 'Ready report line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('adealer.report.wizard', required=True, ondelete='cascade')
    sequence = fields.Integer()
    line_type = fields.Selection([('row', 'Line'), ('total', 'Total')])
    date = fields.Date('Date')
    name = fields.Char('Name')
    ref2 = fields.Char()
    ref3 = fields.Char()
    state = fields.Char('Status')
    qty = fields.Float('Qty', digits=(16, 2))
    currency_id = fields.Many2one('res.currency')
    amount = fields.Monetary('Amount', currency_field='currency_id')
    amount2 = fields.Monetary('Amount 2', currency_field='currency_id')
    amount3 = fields.Monetary('Amount 3', currency_field='currency_id')
    res_model = fields.Char()
    res_id = fields.Integer()

    def action_open(self):
        self.ensure_one()
        if not (self.res_model and self.res_id):
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
        }

# -*- coding: utf-8 -*-
"""Постачальник даних для дашборду «Головна».

AbstractModel (без таблиці) з єдиним методом get_data(dash_type, date_from, date_to),
який фронтенд (OWL client action) викликає через call_kw. Повертає KPI-плитки, місячні
ряди для графіка й допоміжні списки — окремо для кожного типу дашборду:
  showroom  — Автосалон (dealer.car)
  service   — Автосервіс (repair.order / repair.line)
  parts     — Автозапчастини (repair.line запчастини + склад product.product)
"""
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


def _d(s, default):
    """Розпарсити 'YYYY-MM-DD' → date; None/порожнє → default."""
    if not s:
        return default
    if isinstance(s, date):
        return s
    return datetime.strptime(s[:10], '%Y-%m-%d').date()


def _months(dfrom, dto):
    """Список (перше-число-місяця, 'MM.YYYY') від dfrom до dto включно."""
    cur = dfrom.replace(day=1)
    out = []
    last = dto.replace(day=1)
    while cur <= last:
        out.append((cur, cur.strftime('%m.%Y')))
        cur += relativedelta(months=1)
    return out


class AdealerDashboard(models.AbstractModel):
    _name = 'adealer.dashboard'
    _description = 'Dashboard data provider (Головна)'

    # ------------------------------------------------------------------ API
    @api.model
    def get_data(self, dash_type=None, date_from=None, date_to=None):
        """Дані для вкладки дашборда.

        dash_type=None означає «яку вкладку відкривати першою» — її бере з
        налаштувань (Налаштування → 3A-dealer). Раніше вкладка була зашита в
        JS, тож СТО щоразу починало з порожнього Автосалону.
        Обрану вкладку повертаємо в ключі `tab`, щоб клієнт не робив ДРУГИЙ
        запит лише заради назви.
        """
        if not dash_type:
            dash_type = self.env['ir.config_parameter'].sudo().get_param(
                'adealer.dashboard_default_tab', 'showroom')
        if dash_type not in ('showroom', 'service', 'parts'):
            dash_type = 'showroom'
        dfrom = _d(date_from, date.today().replace(month=1, day=1))
        dto = _d(date_to, date.today())
        if dash_type == 'showroom':
            data = self._showroom(dfrom, dto)
        elif dash_type == 'parts':
            data = self._parts(dfrom, dto)
        else:
            data = self._service(dfrom, dto)
        data['tab'] = dash_type
        return data

    def _currency(self):
        return {'symbol': self.env.company.currency_id.symbol or '',
                'position': self.env.company.currency_id.position}

    # ------------------------------------------------------- Автосалон
    def _showroom(self, dfrom, dto):
        # Продаж авто рахуємо за РЕАЛЬНИМ обʼєктом авто (dealer.car — довідник Автомобілі
        # з 1С: VIN, модель, двигун, коробка, колір), а НЕ за назвою рядка реалізації.
        # Немає авто в базі → немає продажів (для СТО/запчастин салон = 0, і це правильно).
        Car = self.env['dealer.car']
        in_stock = Car.search_count([('status', 'in', ['in_stock', 'reserved'])])
        trade_in = Car.search_count([('is_trade_in', '=', True),
                                     ('status', 'in', ['in_stock', 'reserved'])])
        total_cars = Car.search_count([])

        # Продані за період: авто зі статусом sold/delivered, дата продажу в періоді.
        sold = Car.search([('status', 'in', ['sold', 'delivered'])])
        buckets = {k: {'count': 0, 'amount': 0.0} for k, _lbl in _months(dfrom, dto)}
        recent = []
        sold_count = 0
        sold_amount = 0.0
        for car in sold:
            if car.sale_date:
                sday = car.sale_date
            else:
                sdt = car.sale_order_id.date_order or car.write_date
                sday = sdt.date() if sdt else None
            if not sday or not (dfrom <= sday <= dto):
                continue
            amt = car.sale_price or car.total_price or 0.0
            sold_count += 1
            sold_amount += amt
            mkey = sday.replace(day=1)
            if mkey in buckets:
                buckets[mkey]['count'] += 1
                buckets[mkey]['amount'] += amt
            recent.append({'day': sday, 'name': car.name,
                           'partner': car.partner_id.name or '', 'amount': amt})
        recent.sort(key=lambda r: r['day'], reverse=True)

        series = [{'label': lbl, 'value': buckets[k]['amount'], 'count': buckets[k]['count']}
                  for k, lbl in _months(dfrom, dto)]
        return {
            'currency': self._currency(),
            'kpis': [
                {'label': _('Vehicles in stock'), 'value': in_stock, 'kind': 'int', 'icon': 'fa-car'},
                {'label': _('Vehicles sold in period'), 'value': sold_count, 'kind': 'int', 'icon': 'fa-handshake-o'},
                {'label': _('Vehicle sales in period'), 'value': sold_amount, 'kind': 'money', 'icon': 'fa-money'},
                {'label': _('Trade-in in stock'), 'value': trade_in, 'kind': 'int', 'icon': 'fa-exchange'},
                {'label': _('All vehicles in base'), 'value': total_cars, 'kind': 'int', 'icon': 'fa-database'},
            ],
            'series': {'title': _('Vehicle sales by month'), 'data': series},
            'list': {
                'title': _('Recently sold vehicles'),
                'cols': [_('Date'), _('Vehicle'), _('Buyer'), _('Amount')],
                'rows': [[r['day'].strftime('%d.%m.%Y'), r['name'], r['partner'], {'money': r['amount']}]
                         for r in recent[:12]],
            },
        }

    # ------------------------------------------------------- Автосервіс
    def _service(self, dfrom, dto):
        RO = self.env['repair.order']
        # Ділова дата наряду = schedule_date (create_date може бути датою імпорту).
        dom_period = [('schedule_date', '>=', datetime.combine(dfrom, datetime.min.time())),
                      ('schedule_date', '<=', datetime.combine(dto, datetime.max.time()))]
        period = RO.search(dom_period)
        rev = sum(period.mapped('amount_total'))
        cnt = len(period)
        done = period.filtered(lambda o: o.state == 'done')
        in_work = RO.search_count([('state', 'not in', ['done', 'cancel'])])
        avg = (rev / cnt) if cnt else 0.0

        # ряд: виручка по місяцях (за schedule_date)
        buckets = {k: 0.0 for k, _l in _months(dfrom, dto)}
        for o in period:
            key = o.schedule_date.date().replace(day=1)
            if key in buckets:
                buckets[key] += o.amount_total
        series = [{'label': lbl, 'value': buckets[k]} for k, lbl in _months(dfrom, dto)]

        # Найближчі ремонти: заплановані наперед (schedule_date >= сьогодні, ще не завершені).
        # Якщо майбутніх немає (історичний знімок) — показуємо поточні відкриті наряди.
        today0 = datetime.combine(date.today(), datetime.min.time())
        upcoming = RO.search([('schedule_date', '>=', today0), ('state', 'not in', ['done', 'cancel'])],
                             order='schedule_date asc', limit=12)
        list_title = _('Upcoming repairs (calendar)')
        if not upcoming:
            upcoming = RO.search([('state', 'not in', ['done', 'cancel'])],
                                 order='schedule_date desc', limit=12)
            list_title = _('Repairs in progress')
        rows = []
        for o in upcoming:
            rows.append([o.schedule_date.strftime('%d.%m.%Y %H:%M') if o.schedule_date else '',
                         o.name or '',
                         o.partner_id.name or '',
                         o.vehicle_id.name or '',
                         {'money': o.amount_total}])
        return {
            'currency': self._currency(),
            'kpis': [
                {'label': _('Repair orders in period'), 'value': cnt, 'kind': 'int', 'icon': 'fa-wrench'},
                {'label': _('Service revenue in period'), 'value': rev, 'kind': 'money', 'icon': 'fa-money'},
                {'label': _('In progress now'), 'value': in_work, 'kind': 'int', 'icon': 'fa-cogs'},
                {'label': _('Completed in period'), 'value': len(done), 'kind': 'int', 'icon': 'fa-check'},
                {'label': _('Average ticket'), 'value': avg, 'kind': 'money', 'icon': 'fa-calculator'},
            ],
            'series': {'title': _('Service revenue by month'), 'data': series},
            'list': {
                'title': list_title,
                'cols': [_('When'), _('Order'), _('Customer'), _('Vehicle'), _('Amount')],
                'rows': rows,
            },
        }

    # ------------------------------------------------------- Автозапчастини
    def _parts(self, dfrom, dto):
        Line = self.env['repair.line']
        # Ділова дата = schedule_date наряду (create_date = час імпорту).
        dom = [('product_type', '!=', 'service'),
               ('repair_id.schedule_date', '>=', datetime.combine(dfrom, datetime.min.time())),
               ('repair_id.schedule_date', '<=', datetime.combine(dto, datetime.max.time()))]
        lines = Line.search(dom)
        qty_issued = sum(lines.mapped('product_uom_qty'))
        parts_amount = sum(lines.mapped('price_subtotal'))

        buckets = {k: 0.0 for k, _l in _months(dfrom, dto)}
        for ln in lines:
            cd = ln.repair_id.schedule_date
            if not cd:
                continue
            key = cd.date().replace(day=1)
            if key in buckets:
                buckets[key] += ln.price_subtotal
        series = [{'label': lbl, 'value': buckets[k]} for k, lbl in _months(dfrom, dto)]

        # склад: складські товари (type='consu'), кількість/вартість
        Product = self.env['product.product']
        pdom = [('type', '=', 'consu')]
        if 'is_storable' in Product._fields:
            pdom.append(('is_storable', '=', True))
        prods = Product.search(pdom)
        positions = 0
        stock_value = 0.0
        top = []
        for p in prods:
            qty = p.qty_available or 0.0
            if qty <= 0:
                continue
            positions += 1
            val = qty * (p.standard_price or 0.0)
            stock_value += val
            top.append((qty, p.display_name, val))
        top.sort(reverse=True)
        return {
            'currency': self._currency(),
            'kpis': [
                {'label': _('Stock positions'), 'value': positions, 'kind': 'int', 'icon': 'fa-cubes'},
                {'label': _('Parts issued in period'), 'value': qty_issued, 'kind': 'float', 'icon': 'fa-dolly'},
                {'label': _('Parts sales in period'), 'value': parts_amount, 'kind': 'money', 'icon': 'fa-money'},
                {'label': _('Stock value'), 'value': stock_value, 'kind': 'money', 'icon': 'fa-balance-scale'},
            ],
            'series': {'title': _('Parts sales by month'), 'data': series},
            'list': {
                'title': _('Top stock by quantity'),
                'cols': [_('Product'), _('Qty on hand'), _('Value')],
                'rows': [[nm, {'float': qty}, {'money': val}] for qty, nm, val in top[:12]],
            },
        }

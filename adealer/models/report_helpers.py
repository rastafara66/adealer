# -*- coding: utf-8 -*-
"""Хелпери для друкованих форм (Акт звірки взаєморозрахунків)."""
from odoo import models, api


class ResPartnerRecon(models.Model):
    _inherit = 'res.partner'

    def get_report_company(self):
        """Компанія для друкованих форм (партнери часто без company_id)."""
        return self.company_id or self.env.company

    def get_reconciliation_lines(self):
        """Рядки руху взаєморозрахунків для Акту звірки:
        проведені рядки по рахунках дебіторки/кредиторки, з накопиченим сальдо."""
        self.ensure_one()
        AML = self.env['account.move.line']
        lines = AML.search([
            ('partner_id', '=', self.commercial_partner_id.id),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
        ], order='date, id')
        res, bal = [], 0.0
        for l in lines:
            bal += (l.debit or 0.0) - (l.credit or 0.0)
            res.append({
                'date': l.date,
                'name': l.move_id.name or l.name or '',
                'debit': l.debit or 0.0,
                'credit': l.credit or 0.0,
                'balance': bal,
            })
        return res

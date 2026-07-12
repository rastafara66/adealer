from odoo import models, fields, api

class PartnerChildCleanupWizard(models.TransientModel):
    _name = 'partner.child.cleanup.wizard'
    _description = 'Видалення дочірніх контактів партнерів'

    confirm = fields.Boolean(string="Підтвердити видалення", required=True)

    def action_cleanup(self):
        if not self.confirm:
            return
        child_contacts = self.env['res.partner'].search([('parent_id', '!=', False)])
        count = len(child_contacts)
        child_contacts.unlink()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Видалення завершено',
                'message': f'Видалено {count} дочірніх контактів.',
                'type': 'success',
                'sticky': False,
            }
        }
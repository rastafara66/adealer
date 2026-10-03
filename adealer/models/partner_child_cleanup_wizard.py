from odoo import _, models, fields, api

class PartnerChildCleanupWizard(models.TransientModel):
    _name = 'partner.child.cleanup.wizard'
    _description = 'Delete partner child contacts'

    confirm = fields.Boolean(string="Confirm deletion", required=True,
                             help='Tick to confirm: every child contact in the database will be deleted.')

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
                'title': _('Deletion completed'),
                'message': _('%s child contacts deleted.') % count,
                'type': 'success',
                'sticky': False,
            }
        }
# -*- coding: utf-8 -*-
"""Free the list and kanban slots of the product actions before the XML binds its own views.

From 19.0.1.16.0 the products action opens with the module's list view and
its own kanban card (``ir.actions.act_window.view`` records). An action may
hold only one view per type (``ir_act_window_view_unique_mode_per_action``),
and a database where the action had been bound to some other list view by
hand already holds that slot: the upgrade stopped with "duplicate key value
violates unique constraint" before any of the new views was loaded.

Bindings the module created itself are kept; others for list and kanban on
these two actions are removed, because the module's views replace them.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        DELETE FROM ir_act_window_view v
         USING ir_model_data a
         WHERE a.model = 'ir.actions.act_window'
           AND a.module = 'adealer'
           AND a.name IN ('action_window_products', 'action_window_products_by_group')
           AND v.act_window_id = a.res_id
           AND v.view_mode IN ('list', 'kanban')
           AND NOT EXISTS (
                SELECT 1 FROM ir_model_data d
                 WHERE d.model = 'ir.actions.act_window.view'
                   AND d.module = 'adealer'
                   AND d.res_id = v.id)
        RETURNING v.id, v.view_mode, v.view_id
    """)
    for row_id, mode, view_id in cr.fetchall():
        _logger.info("products action: removed the %s binding %s (view %s); "
                     "the module's own view takes its place", mode, row_id, view_id)

# -*- coding: utf-8 -*-
from odoo import api, models, _

class StockWarehouseOrderpoint(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    def _log_reorder(self, route_action, qty, uom, created_doc=None, note=None):
        """Create a log entry for the systray/bell."""
        self.ensure_one()
        vals = {
            'company_id': self.company_id.id or self.env.company.id,
            'product_id': self.product_id.id,
            'orderpoint_id': self.id,
            'action_type': route_action,           # 'purchase' or 'manufacture'
            'product_qty': qty or 0.0,
            'product_uom_id': (uom and uom.id) or (self.product_uom and self.product_uom.id),
            'note': note or '',
            'opened': False,
            'name': 'Open',
        }
        if created_doc:
            vals.update({
                'created_doc_model': created_doc._name,
                'created_doc_id': created_doc.id,
            })
        return self.env['op.reorder.trigger.log'].sudo().create(vals)

    # v18 signature includes raise_user_error; accept **kwargs to be future-proof
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=False, raise_user_error=True, **kwargs):
        """Call super; logging is handled in PO line/MO hooks."""
        return super()._procure_orderpoint_confirm(
            use_new_cursor=use_new_cursor,
            company_id=company_id,
            raise_user_error=raise_user_error,
            **kwargs,
        )

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Log newly created MOs (likely from reordering rules / scheduler).
        for mo in records.sudo():
            try:
                op = self.env['stock.warehouse.orderpoint'].sudo().search(
                    [('product_id', '=', mo.product_id.id),
                     ('company_id', '=', mo.company_id.id)], limit=1
                )
                if op:
                    op._log_reorder(
                        route_action='manufacture',
                        qty=mo.product_qty,
                        uom=mo.product_uom_id,
                        created_doc=mo,
                        note=_('Created from Manufacturing Order %s') % (mo.name or mo.id),
                    )
            except Exception:
                continue
        return records

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        Log = self.env['op.reorder.trigger.log'].sudo()
        Orderpoint = self.env['stock.warehouse.orderpoint'].sudo()

        # Group by (order, product, uom) within this create batch
        grouped = {}
        for line in lines.sudo():
            try:
                if line.display_type or not line.product_id or not line.order_id:
                    continue
                key = (line.order_id.id, line.product_id.id, line.product_uom.id)
                grouped.setdefault(key, 0.0)
                grouped[key] += line.product_qty
            except Exception:
                continue

        # Create one log per grouped key, if an orderpoint exists for the product/company
        for (order_id, product_id, uom_id), qty in grouped.items():
            try:
                po = self.env['purchase.order'].sudo().browse(order_id)
                if not po.exists():
                    continue
                op = Orderpoint.search([
                    ('product_id', '=', product_id),
                    ('company_id', '=', po.company_id.id),
                ], limit=1)
                if not op:
                    continue
                Log.create({
                    'company_id': po.company_id.id,
                    'product_id': product_id,
                    'orderpoint_id': op.id,
                    'action_type': 'purchase',
                    'product_qty': qty,
                    'product_uom_id': uom_id,
                    'note': _('Created from Purchase Order %s') % (po.name or po.id),
                    'opened': False,
                    'name': 'Open',
                    'created_doc_model': 'purchase.order',
                    'created_doc_id': order_id,
                })
            except Exception:
                continue

        return lines

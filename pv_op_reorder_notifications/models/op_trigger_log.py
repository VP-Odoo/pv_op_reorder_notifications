# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class OpReorderTriggerLog(models.Model):
    _name = "op.reorder.trigger.log"
    _description = "Reorder Trigger Log"
    _order = "triggered_on desc, id desc"

    # Basic data
    name = fields.Char(string="Status", default="Open", readonly=True)
    triggered_on = fields.Datetime(string="Triggered On", default=fields.Datetime.now, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda s: s.env.company, index=True)

    # What/why
    product_id = fields.Many2one('product.product', string="Product", index=True)
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string="Orderpoint", ondelete="set null")
    action_type = fields.Selection([
        ('purchase', 'Purchase'),
        ('manufacture', 'Manufacture'),
    ], string="Action", index=True)
    product_qty = fields.Float(string="Quantity", digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', string="UoM")
    note = fields.Text(string="Note")

    # Target document (PO/MO/etc.)
    created_doc_model = fields.Char(string="Document Model")
    created_doc_id = fields.Integer(string="Document ID")

    # Clickable reference to the document
    created_doc_ref = fields.Reference(
        selection=lambda self: self._ref_selection(),
        string="Document",
        compute="_compute_created_doc_ref",
        store=False,
    )

    # State
    opened = fields.Boolean(string="Opened", default=False, index=True)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    @api.model
    def _ref_selection(self):
        return [
            ('purchase.order', _('Request for Quotation / Purchase Order')),
            ('mrp.production', _('Manufacturing Order')),
        ]

    @api.depends('created_doc_model', 'created_doc_id')
    def _compute_created_doc_ref(self):
        valid_models = {m for m, _ in self._ref_selection()}
        for rec in self:
            if rec.created_doc_model in valid_models and rec.created_doc_id:
                rec.created_doc_ref = f"{rec.created_doc_model},{rec.created_doc_id}"
            else:
                rec.created_doc_ref = False

    @api.model
    def op_unread_count(self):
        domain = [('opened', '=', False)]
        if self.env.company:
            domain.append(('company_id', '=', self.env.company.id))
        return self.search_count(domain)

    def _mark_as_opened(self):
        unopened = self.filtered(lambda r: not r.opened)
        if unopened:
            unopened.write({'opened': True, 'name': 'Opened'})

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_open_and_mark(self):
        """Explicit button: mark opened and jump to related doc (if any)."""
        self.ensure_one()
        self._mark_as_opened()
        if self.created_doc_model and self.created_doc_id:
            Model = self.env[self.created_doc_model].sudo()
            browsed = Model.browse(self.created_doc_id)
            if not browsed.exists():
                raise UserError(_("The related document no longer exists."))
            return {
                'type': 'ir.actions.act_window',
                'res_model': self.created_doc_model,
                'res_id': self.created_doc_id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # -------------------------------------------------------------------------
    # Auto-mark as opened when a single record is read (form open).
    # This won't trigger for list loads (which read many records at once).
    # Signature normalized across v17/v18.
    # -------------------------------------------------------------------------
    def web_read(self, specification=None, **kwargs):
        if specification is None:
            specification = kwargs.get('specification') or kwargs.get('fields') or []
        # If a single record is being read (form open), mark it as opened first
        if len(self) == 1:
            try:
                self.sudo()._mark_as_opened()
            except Exception:
                pass
        return super().web_read(specification)

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OpReorderTriggerLog(models.Model):
    _name = "op.reorder.trigger.log"
    _description = "Reorder Trigger Log"
    _order = "triggered_on desc, id desc"

    # -------------------------------------------------------------------------
    # Basic data
    # -------------------------------------------------------------------------
    name = fields.Char(string="Status", default="Open", readonly=True)
    triggered_on = fields.Datetime(string="Triggered On", default=fields.Datetime.now, readonly=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda s: s.env.company,
        index=True,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # What/why
    # -------------------------------------------------------------------------
    product_id = fields.Many2one('product.product', string="Product", index=True, readonly=True)
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string="Reorder Rule", index=True, readonly=True)

    # Canonical keys only (avoid duplicate xmlids); legacy values normalized in create/write
    action_type = fields.Selection(
        [
            ('purchase', 'Purchase'),
            ('manufacture', 'Manufacture'),
        ],
        string="Action",
        readonly=True,
        index=True,
    )

    product_qty = fields.Float(string="Qty", readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string="UoM", readonly=True)
    note = fields.Char(string="Note", readonly=True)

    # Whether the user has opened/seen this notification (used by systray bell)
    opened = fields.Boolean(string="Opened", default=False, readonly=True, index=True)

    # -------------------------------------------------------------------------
    # Clickable reference to the created document (RFQ/PO or MO)
    # -------------------------------------------------------------------------
    created_doc_model = fields.Char(string="Document Model", readonly=True)
    created_doc_id = fields.Integer(string="Document ID", readonly=True)

    def _ref_selection(self):
        """Allowed reference targets (include mrp.production for MO clickability)."""
        return [
            ('purchase.order', _('Request for Quotation / Purchase Order')),
            ('mrp.production',  _('Manufacturing Order')),
        ]

    created_doc_ref = fields.Reference(
        selection=_ref_selection,
        string="Document",
        compute="_compute_created_doc_ref",
        readonly=True,
        store=False,
    )

    @api.depends('created_doc_model', 'created_doc_id')
    def _compute_created_doc_ref(self):
        """Compute the 'model,id' string expected by the Reference widget."""
        valid_models = {'purchase.order', 'mrp.production'}
        for rec in self:
            if rec.created_doc_model in valid_models and rec.created_doc_id:
                rec.created_doc_ref = f"{rec.created_doc_model},{rec.created_doc_id}"
            else:
                rec.created_doc_ref = False

    # -------------------------------------------------------------------------
    # Normalization for legacy values + standard CRUD hooks
    # -------------------------------------------------------------------------
    @staticmethod
    def _normalize_action_type(value):
        """Map legacy/case variants to canonical keys."""
        if not value:
            return value
        mapping = {
            'Purchase': 'purchase',
            'Manufacture': 'manufacture',
            'purchase': 'purchase',
            'manufacture': 'manufacture',
        }
        return mapping.get(value, value)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'action_type' in vals:
                vals['action_type'] = self._normalize_action_type(vals.get('action_type'))
        return super().create(vals_list)

    def write(self, vals):
        if 'action_type' in vals:
            vals['action_type'] = self._normalize_action_type(vals.get('action_type'))
        return super().write(vals)

    # -------------------------------------------------------------------------
    # Helpers & UI actions
    # -------------------------------------------------------------------------
    def _mark_as_opened(self):
        """Mark record(s) as opened (boolean only; keep all other fields intact)."""
        to_update = self.filtered(lambda r: not r.opened)
        if to_update:
            # readonly=True in field definition only affects the UI, not server writes
            to_update.write({'opened': True})

    def action_open_and_mark(self):
        """
        Called by the header button in the form view.
        - Marks the notification as opened.
        - Opens the referenced RFQ/PO or MO in form view (generic window action).
        """
        self.ensure_one()
        try:
            self.sudo()._mark_as_opened()
        except Exception:
            # Never block navigation because of this helper
            pass

        if not self.created_doc_model or not self.created_doc_id:
            return False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Document'),
            'res_model': self.created_doc_model,
            'view_mode': 'form',
            'target': 'current',
            'res_id': int(self.created_doc_id),
        }

    # Normalize across versions: when a single record form is opened, mark opened
    def web_read(self, specification=None, **kwargs):
        if specification is None:
            specification = kwargs.get('specification') or kwargs.get('fields') or []
        if len(self) == 1:
            try:
                self.sudo()._mark_as_opened()
            except Exception:
                # Never block reads because of this helper
                pass
        return super().web_read(specification)

    # -------------------------------------------------------------------------
    # Systray badge uses this to fetch unread count
    # -------------------------------------------------------------------------
    @api.model
    def op_unread_count(self):
        """Return count of unopened notifications for the current user's context."""
        domain = [('opened', '=', False)]
        # Respect allowed companies if present; fine for single-company too.
        company_ids = self.env.context.get('allowed_company_ids')
        if company_ids:
            domain.append(('company_id', 'in', company_ids))
        return self.search_count(domain)

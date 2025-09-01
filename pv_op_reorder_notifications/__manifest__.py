# -*- coding: utf-8 -*-
{
    'name': 'OP Reorder Notifications',
    'version': '18.0.1.0.0',
    'summary': 'Systray notifications and log for reordering (PO/MO) events',
    "author": "PV-Odoo",
    'license': 'LGPL-3',
    'category': 'Inventory/Inventory',
    "images": ["static/description/banner.png"],
    'currency': 'EUR',
    'depends': [
        'stock',
        'purchase',   # needed because we hook purchase.order.create
        'mrp',        # needed because we hook mrp.production.create
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/op_reorder_notifications_security.xml',
        'views/op_trigger_log_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pv_op_reorder_notifications/static/src/js/systray_reorder_bell.js',
        ],
    },
    'installable': True,
    'application': False,
    "description": """
Reorder Notifications

This module provides a real-time notification system for low-stock events based on product reordering rules.
It ensures that users are instantly alerted when a reorder point is triggered, allowing quick action to replenish stock.

Features:
Systray Bell Icon: Displays the current number of unread reorder notifications directly in the top menu.

Click to View: Clicking the bell opens a list of reorder triggers with full details.

Clickable Document Links: Jump directly to the related RFQ, Purchase Order, or Manufacturing Order from the notification list.

Automatic Opened Flag: Notifications are marked as opened automatically when viewed.

Scheduler Integration: Notifications are created whenever Odoo’s procurement scheduler runs and triggers a reordering rule.

Support for Multiple Actions: Works for both Purchase and Manufacture actions from reordering rules.

Benefits:
No more missed reorders — stay informed the moment stock falls below minimum levels.

Quick access to the relevant documents to act without searching.

Seamless integration with standard Odoo scheduling and procurement flows.

Improves inventory control and reduces the risk of stockouts.

""",
}

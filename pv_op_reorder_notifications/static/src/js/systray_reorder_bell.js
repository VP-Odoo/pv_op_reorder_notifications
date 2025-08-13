/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ReorderBell extends Component {
    static template = xml/* xml */ `
<div class="o_systray_item o_reorder_bell">
  <a href="#" t-on-click.prevent="openLog" title="Reorder notifications" class="o_reorder_bell_link">
    <i class="fa fa-bell"/>
    <t t-if="state.count">
      <span class="badge rounded-pill bg-danger o_systrayCounter">
        <t t-esc="state.count"/>
      </span>
    </t>
  </a>
</div>
`;

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ count: 0, loading: true });
        this._intervalId = null;

        onMounted(async () => {
            await this._refreshCount();
            this._intervalId = setInterval(() => this._refreshCount(), 15000);
        });
        onWillUnmount(() => {
            if (this._intervalId) clearInterval(this._intervalId);
        });
    }

    async _refreshCount() {
        try {
            const count = await this.orm.call(
                "op.reorder.trigger.log",
                "op_unread_count",
                [],
                {}
            );
            this.state.count = Number(count) || 0;
            this.state.loading = false;
        } catch (e) {
            this.state.loading = false;
        }
    }

    async openLog() {
        // IMPORTANT: XML ID namespace uses the module (folder) name
        await this.action.doAction("pv_op_reorder_notifications.action_op_trigger_log");
        await this._refreshCount();
    }
}

// The registry key label is arbitrary, but rename it to match the module for clarity
registry.category("systray").add(
    "pv_op_reorder_notifications.ReorderBell",
    { Component: ReorderBell },
    { sequence: 60 }
);

// Inject CSS for perfect alignment + solid white icon
const style = document.createElement('style');
style.textContent = `
.o_reorder_bell {
    display: inline-flex;
    align-items: center;
    height: 100%;
}
.o_reorder_bell_link {
    display: inline-flex;
    align-items: center;
    line-height: 1;
}
.o_reorder_bell i.fa-bell {
    font-size: 18px;
    color: #ffffff; /* solid white bell */
    vertical-align: middle;
    line-height: 1;
    position: relative;
    top: -1px;     /* fine baseline alignment with bubble icon */
}
.o_reorder_bell .o_systrayCounter {
    margin-left: 2px;
    vertical-align: middle;
}
`;
document.head.appendChild(style);

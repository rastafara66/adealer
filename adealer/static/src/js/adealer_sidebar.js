/** @odoo-module **/

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

const APP_XMLID = "adealer.menu_root";

export class AdealerSidebar extends Component {
    static template = "adealer.Sidebar";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.state = useState({
            enabled: !!session.adealer_sidebar_enabled,
            collapsed: false,
            inApp: false,
            groups: [],
            expanded: {},
        });
        this._onAppChanged = () => this._update();
        onWillStart(() => this._update());
        this.env.bus.addEventListener("MENUS:APP-CHANGED", this._onAppChanged);
        onWillUnmount(() => {
            this.env.bus.removeEventListener("MENUS:APP-CHANGED", this._onAppChanged);
            this._setBody(false, false, false);
        });
    }

    _update() {
        let inApp = false;
        let groups = [];
        try {
            const app = this.menuService.getCurrentApp();
            inApp = !!(app && app.xmlid === APP_XMLID);
            if (inApp) {
                const tree = this.menuService.getMenuAsTree(app.id);
                groups = (tree && tree.childrenTree) || [];
            }
        } catch (e) {
            inApp = false;
            groups = [];
        }
        this.state.inApp = inApp;
        this.state.groups = groups;
        this._setBody(inApp, this.state.enabled && inApp, this.state.collapsed);
    }

    isExpanded(id) {
        // за замовчуванням усі розділи (і вкладені підрозділи) згорнуті
        return this.state.expanded[id] === true;
    }

    toggleGroup(id) {
        this.state.expanded[id] = !this.isExpanded(id);
    }

    _setBody(inApp, hasSidebar, collapsed) {
        try {
            // Фірмова тема (navy/gold) — глобально по всьому бекенду, коли увімкнено
            document.body.classList.toggle("adealer-theme", !!this.state.enabled);
            document.body.classList.toggle("adealer-app", !!inApp);
            document.body.classList.toggle("adealer-has-sidebar", !!hasSidebar);
            document.body.classList.toggle("adealer-sidebar-collapsed", !!collapsed);
        } catch (e) {
            // no-op
        }
    }

    toggle() {
        this.state.collapsed = !this.state.collapsed;
        this._setBody(this.state.inApp, this.state.enabled && this.state.inApp, this.state.collapsed);
    }

    onSelect(menu) {
        if (menu) {
            this.menuService.selectMenu(menu);
        }
    }
}

registry.category("main_components").add("adealer.Sidebar", { Component: AdealerSidebar });

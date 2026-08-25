/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
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
        this._onAppChanged = () => { this._update(); this._syncTop(); };
        this._onResize = () => this._syncTop();
        onWillStart(() => this._update());
        this.env.bus.addEventListener("MENUS:APP-CHANGED", this._onAppChanged);
        onMounted(() => {
            this._syncTop();
            // Банер нейтралізації на демо-базі домальовується після монтування
            // й зсуває навбар — переміряти на наступному кадрі.
            requestAnimationFrame(() => this._syncTop());
            window.addEventListener("resize", this._onResize);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("MENUS:APP-CHANGED", this._onAppChanged);
            window.removeEventListener("resize", this._onResize);
            this._setBody(false, false, false);
        });
    }

    // Прив'язати верх сайдбара до РЕАЛЬНОГО низу навбара (не хардкод 46px):
    // на демо згори висить банер нейтралізації, що зсуває навбар униз.
    _syncTop() {
        try {
            const nav = document.querySelector(".o_main_navbar");
            const top = nav ? Math.round(nav.getBoundingClientRect().bottom) : 46;
            document.documentElement.style.setProperty("--adealer-sb-top", top + "px");
        } catch (e) {
            // no-op
        }
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

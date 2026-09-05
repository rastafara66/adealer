/** @odoo-module **/
// Бічне меню теми 3A-dealer.
//
// 🔴 Відмінність від сайдбара, що живе в самому додатку `adealer`: той
// прив'язаний до одного застосунку (`APP_XMLID = "adealer.menu_root"`) і
// вмикається окремим прапорцем. Цей — темовий, тобто працює в БУДЬ-ЯКОМУ
// застосунку Odoo: тема продається окремо від додатка, і покупець, який поставив
// саму тему, має отримати меню скрізь, а не в чужому для нього 3A-dealer.
//
// 🔴 Захист від ДВОХ сайдбарів. Якщо стоїть і додаток `adealer`, і його власний
// сайдбар увімкнено, то всередині 3A-dealer було б два однакових меню одне на
// одному. Тому темовий мовчки поступається: перевіряємо той самий прапорець
// сесії, яким керується сайдбар додатка. Це дешевше й надійніше, ніж
// домовлятися між модулями, і працює навіть якщо тему поставили першою.
//
// Патерн узято з уже відлагодженого `fop_theme` (тема «Актива»): розходитись
// двом копіям того самого коду сенсу немає.

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

// Застосунок, чий власний сайдбар має пріоритет над темовим.
const OWNER_APP_XMLID = "adealer.menu_root";

export class AdealerThemeSidebar extends Component {
    static template = "adealer_theme.Sidebar";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.state = useState({
            enabled: true,
            collapsed: false,
            visible: false,
            // Назва застосунку тримається в стані, а не читається з сервісу в
            // шаблоні: `getCurrentApp()` може віддати null (перехід між
            // застосунками, вихід на домашній екран), і `.name` у розмітці
            // впав би вже після того, як компонент вирішив показатись.
            appName: "",
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
            this._setBody(false, false);
        });
    }

    // Верх сайдбара прив'язаний до РЕАЛЬНОГО низу навбара, а не до хардкоду
    // 46px: на нейтралізованій демо-базі згори з'являється банер, що зсуває
    // навбар, і сайдбар із фіксованим top накривав би верхнє меню.
    _syncTop() {
        try {
            const nav = document.querySelector(".o_main_navbar");
            const top = nav ? Math.round(nav.getBoundingClientRect().bottom) : 46;
            document.documentElement.style.setProperty("--adt-sb-top", top + "px");
        } catch (e) {
            // no-op
        }
    }

    _update() {
        let visible = false;
        let groups = [];
        let appName = "";
        try {
            const app = this.menuService.getCurrentApp();
            if (app) {
                appName = app.name || "";
                // Поступаємось власному сайдбару додатка 3A-dealer.
                const ownerHasItsOwn = app.xmlid === OWNER_APP_XMLID
                    && !!session.adealer_sidebar_enabled;
                if (!ownerHasItsOwn) {
                    const tree = this.menuService.getMenuAsTree(app.id);
                    groups = (tree && tree.childrenTree) || [];
                    // Показуємо лише там, де є що показати: застосунок без
                    // підменю дав би порожню смугу, яка з'їдає ширину екрана.
                    visible = groups.length > 0;
                }
            }
        } catch (e) {
            visible = false;
            groups = [];
            appName = "";
        }
        this.state.visible = visible;
        this.state.appName = appName;
        this.state.groups = groups;
        this._setBody(this.state.enabled && visible, this.state.collapsed);
    }

    isExpanded(id) {
        return this.state.expanded[id] === true;
    }

    toggleGroup(id) {
        this.state.expanded[id] = !this.isExpanded(id);
    }

    _setBody(hasSidebar, collapsed) {
        try {
            document.body.classList.toggle("adt-has-sidebar", !!hasSidebar);
            document.body.classList.toggle("adt-sidebar-collapsed", !!collapsed);
        } catch (e) {
            // no-op
        }
    }

    toggle() {
        this.state.collapsed = !this.state.collapsed;
        this._setBody(this.state.enabled && this.state.visible, this.state.collapsed);
    }

    onSelect(menu) {
        if (menu) {
            this.menuService.selectMenu(menu);
        }
    }
}

registry.category("main_components")
    .add("adealer_theme.Sidebar", { Component: AdealerThemeSidebar });

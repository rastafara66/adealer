/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// Типи дашбордів (вкладки перемикача)
const TYPES = [
    { id: "showroom", label: _t("Showroom"), icon: "fa-car" },
    { id: "service", label: _t("Service"), icon: "fa-wrench" },
    { id: "parts", label: _t("Parts"), icon: "fa-cubes" },
];

function todayISO() {
    return new Date().toISOString().slice(0, 10);
}
function yearStartISO() {
    return new Date().getFullYear() + "-01-01";
}

export class AdealerDashboard extends Component {
    static template = "adealer.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.types = TYPES;
        this.state = useState({
            // Порожньо, а не "showroom": першу вкладку називає СЕРВЕР за
            // налаштуванням (Налаштування → 3A-dealer). Інакше СТО щоразу
            // відкривало порожній Автосалон.
            type: null,
            date_from: yearStartISO(),
            date_to: todayISO(),
            loading: true,
            data: null,
        });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("adealer.dashboard", "get_data", [
                this.state.type,
                this.state.date_from,
                this.state.date_to,
            ]);
            // Перший виклик іде з type=null — сервер сам обирає вкладку за
            // налаштуванням і повертає її назву.
            if (this.state.data && this.state.data.tab) {
                this.state.type = this.state.data.tab;
            }
        } finally {
            this.state.loading = false;
        }
    }

    setType(id) {
        if (this.state.type === id) {
            return;
        }
        this.state.type = id;
        this.load();
    }

    onDate(which, ev) {
        this.state[which] = ev.target.value;
    }

    // --- форматування ---
    fmtMoney(v) {
        const c = (this.state.data && this.state.data.currency) || {};
        const n = (v || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return c.position === "before" ? `${c.symbol} ${n}` : `${n} ${c.symbol || ""}`.trim();
    }
    fmtInt(v) {
        return (v || 0).toLocaleString();
    }
    fmtFloat(v) {
        return (v || 0).toLocaleString(undefined, { maximumFractionDigits: 3 });
    }
    fmtKpi(k) {
        if (k.kind === "money") return this.fmtMoney(k.value);
        if (k.kind === "float") return this.fmtFloat(k.value);
        return this.fmtInt(k.value);
    }
    // клітинка списку може бути {money: x} / {float: x} / рядком
    fmtCell(cell) {
        if (cell && typeof cell === "object") {
            if ("money" in cell) return this.fmtMoney(cell.money);
            if ("float" in cell) return this.fmtFloat(cell.float);
        }
        return cell;
    }

    // геометрія стовпчикового графіка (inline SVG, без зовнішніх бібліотек)
    get bars() {
        const data = (this.state.data && this.state.data.series && this.state.data.series.data) || [];
        const max = Math.max(1, ...data.map((d) => d.value || 0));
        const n = data.length || 1;
        const bw = 100 / n; // ширина слота у %
        return data.map((d, i) => ({
            label: d.label,
            value: d.value || 0,
            valueLabel: this.fmtMoney(d.value || 0),
            x: i * bw + bw * 0.15,
            w: bw * 0.7,
            h: Math.max(0.5, ((d.value || 0) / max) * 100),
            y: 100 - Math.max(0.5, ((d.value || 0) / max) * 100),
        }));
    }
}

registry.category("actions").add("adealer_dashboard", AdealerDashboard);

/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// luxon постачається Odoo як ГЛОБАЛ (web/static/lib/luxon), а не як ES-модуль "luxon".
const { DateTime } = luxon;

// Вікно робочого дня на дошці (години)
const DAY_START = 7;
const DAY_END = 21;
const PALETTE = ["#1a3a6b", "#0e7c5a", "#8a5a00", "#7a1f5a", "#155e75",
                 "#9a3412", "#3f6212", "#5b21b6", "#9f1239", "#374151"];

export class AdealerBookingBoard extends Component {
    static template = "adealer.BookingBoard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            date: DateTime.local().toISODate(),
            posts: [],
            byPost: {},        // workplace_id -> [booking layout objs]
            loading: true,
        });
        this.hours = [];
        for (let h = DAY_START; h <= DAY_END; h++) {
            this.hours.push(h);
        }
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            const day = DateTime.fromISO(this.state.date);
            // межі дня в локальному TZ → UTC (Odoo зберігає UTC)
            const startUtc = day.startOf("day").toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
            const endUtc = day.plus({ days: 1 }).startOf("day").toUTC().toFormat("yyyy-MM-dd HH:mm:ss");

            const posts = await this.orm.searchRead(
                "adealer.workplace", [["active", "=", true]],
                ["id", "name", "color"], { order: "sequence, name" });

            const recs = await this.orm.searchRead(
                "adealer.service.booking",
                [["appointment_datetime", ">=", startUtc], ["appointment_datetime", "<", endUtc]],
                ["id", "appointment_datetime", "work_duration", "workplace_id", "plate",
                 "vehicle_id", "requested_works", "employee_id", "partner_id", "state"],
                { order: "appointment_datetime" });

            const byPost = {};
            for (const p of posts) {
                byPost[p.id] = [];
            }
            byPost[0] = byPost[0] || []; // без поста
            const span = DAY_END - DAY_START;
            for (const r of recs) {
                // UTC → локальний час для позиціонування
                const dt = DateTime.fromSQL(r.appointment_datetime, { zone: "utc" }).toLocal();
                const startH = dt.hour + dt.minute / 60;
                const dur = r.work_duration || 0.5;
                let top = ((startH - DAY_START) / span) * 100;
                let height = (dur / span) * 100;
                if (top < 0) { height += top; top = 0; }
                if (top + height > 100) { height = 100 - top; }
                if (height < 2) { height = 2; }
                const wpId = r.workplace_id ? r.workplace_id[0] : 0;
                (byPost[wpId] = byPost[wpId] || []).push({
                    id: r.id,
                    top, height,
                    time: dt.toFormat("HH:mm"),
                    plate: r.plate || (r.vehicle_id ? r.vehicle_id[1] : ""),
                    works: (r.requested_works || "").slice(0, 60),
                    mechanic: r.employee_id ? r.employee_id[1] : "",
                    partner: r.partner_id ? r.partner_id[1] : "",
                    done: r.state === "done",
                });
            }
            this.state.posts = posts;
            this.state.byPost = byPost;
        } finally {
            this.state.loading = false;
        }
    }

    postColor(i) {
        return PALETTE[i % PALETTE.length];
    }
    postBookings(postId) {
        return this.state.byPost[postId] || [];
    }
    get noPostBookings() {
        return this.state.byPost[0] || [];
    }
    hourLabel(h) {
        return String(h).padStart(2, "0") + ":00";
    }

    prevDay() {
        this.state.date = DateTime.fromISO(this.state.date).minus({ days: 1 }).toISODate();
        this.load();
    }
    nextDay() {
        this.state.date = DateTime.fromISO(this.state.date).plus({ days: 1 }).toISODate();
        this.load();
    }
    today() {
        this.state.date = DateTime.local().toISODate();
        this.load();
    }
    onDate(ev) {
        this.state.date = ev.target.value;
        this.load();
    }
    get dateLabel() {
        return DateTime.fromISO(this.state.date).setLocale("uk").toFormat("cccc, d LLLL yyyy");
    }

    openBooking(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "adealer.service.booking",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
    toPeriods() {
        this.action.doAction("adealer.action_service_bookings");
    }
}

registry.category("actions").add("adealer_booking_board", AdealerBookingBoard);

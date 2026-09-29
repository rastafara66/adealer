/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

// luxon постачається Odoo як ГЛОБАЛ (web/static/lib/luxon), а не як ES-модуль "luxon".
const { DateTime } = luxon;

// Робочий день за замовчуванням (години). Дошка розширює його сама, якщо
// записи виходять за межі: запис, якого не видно на дошці, — найгірше, що
// може показати розклад (у 1С поза шкалою запис просто зникає).
const DAY_START = 9;
const DAY_END = 18;
const HOUR_PX = 64;
const SLOT_MINUTES = 15;
// Скільки днів уперед — кнопками, як у розкладі 1С (сьогодні + 14).
const QUICK_DAYS = 15;
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
            dayStart: DAY_START,
            dayEnd: DAY_END,
            loading: true,
        });
        onWillStart(() => this.load());
    }

    // 🔴 Мову дат не задаємо самі: Odoo вже налаштувала luxon на мову
    // користувача. Тут стояло `setLocale("uk")` — і англомовний покупець
    // бачив дні тижня українською.

    get hours() {
        const out = [];
        for (let h = this.state.dayStart; h < this.state.dayEnd; h++) {
            out.push(h);
        }
        return out;
    }

    get laneHeight() {
        return (this.state.dayEnd - this.state.dayStart) * HOUR_PX;
    }

    get quickDays() {
        const today = DateTime.local().startOf("day");
        const out = [];
        for (let i = 0; i < QUICK_DAYS; i++) {
            const d = today.plus({ days: i });
            out.push({
                iso: d.toISODate(),
                label: d.toFormat("dd.MM ccc"),
                weekend: d.weekday >= 6,
            });
        }
        return out;
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
                ["id", "appointment_datetime", "stop_datetime", "work_duration", "workplace_id",
                 "plate", "model_id", "vehicle_id", "partner_id", "customer_name", "phone",
                 "requested_works", "repair_type_id", "repair_type_color", "advisor_id",
                 "employee_id", "sale_order_id", "intake_time", "state"],
                { order: "appointment_datetime" });

            // Вікно дня: робочі години, розширені до крайніх записів.
            let dayStart = DAY_START;
            let dayEnd = DAY_END;
            const items = recs.map((r) => {
                const start = DateTime.fromSQL(r.appointment_datetime, { zone: "utc" }).toLocal();
                const stop = r.stop_datetime
                    ? DateTime.fromSQL(r.stop_datetime, { zone: "utc" }).toLocal()
                    : start.plus({ minutes: Math.round((r.work_duration || 0.5) * 60) });
                const startH = start.hour + start.minute / 60;
                const stopH = stop.hasSame(start, "day") ? stop.hour + stop.minute / 60 : 24;
                dayStart = Math.min(dayStart, Math.floor(startH));
                dayEnd = Math.max(dayEnd, Math.ceil(stopH));
                return { r, start, stop, startH, stopH };
            });
            dayEnd = Math.min(dayEnd, 24);

            const byPost = {};
            for (const p of posts) {
                byPost[p.id] = [];
            }
            byPost[0] = [];
            const span = dayEnd - dayStart;
            for (const { r, start, stop, startH, stopH } of items) {
                const top = ((startH - dayStart) / span) * 100;
                const height = Math.max(((stopH - startH) / span) * 100, 1.5);
                const car = [r.plate, r.model_id ? r.model_id[1].split("/").pop() : ""]
                    .filter(Boolean).join(" ") || (r.vehicle_id ? r.vehicle_id[1] : "");
                const customer = r.partner_id ? r.partner_id[1] : (r.customer_name || "");
                // 🔴 `_t()` — лише поза шаблонними рядками (`${…}`): екстрактор
                // перекладів Odoo їх не бачить, і підпис лишився б англійським
                // у всіх мовах, а гейт перекладів — зеленим.
                const lines = [
                    ["time", start.toFormat("HH:mm") + "–" + stop.toFormat("HH:mm")],
                    ["type", r.repair_type_id ? r.repair_type_id[1] : ""],
                    ["car", car],
                    ["customer", customer],
                    ["works", (r.requested_works || "").trim()],
                    ["phone", r.phone ? _t("tel.") + " " + r.phone : ""],
                    ["advisor", r.advisor_id ? _t("Advisor") + ": " + r.advisor_id[1] : ""],
                    ["mechanic", r.employee_id ? r.employee_id[1] : ""],
                    // Назва замовлення вже каже, що це замовлення, — без префікса.
                    ["order", r.sale_order_id ? r.sale_order_id[1] : ""],
                ].filter(([, text]) => text);
                const wpId = r.workplace_id && byPost[r.workplace_id[0]] ? r.workplace_id[0] : 0;
                byPost[wpId].push({
                    id: r.id,
                    top, height,
                    lines,
                    tooltip: lines.map(([, text]) => text).join("\n"),
                    color: r.repair_type_color || "",
                    done: r.state === "done",
                    cancelled: r.state === "cancel",
                });
            }
            this.state.posts = posts;
            this.state.byPost = byPost;
            this.state.dayStart = dayStart;
            this.state.dayEnd = dayEnd;
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
    eventStyle(b, postIndex) {
        const edge = b.color || this.postColor(postIndex);
        let fill = "";
        if (/^#[0-9a-fA-F]{6}$/.test(b.color)) {
            // Колір виду ремонту приходить яким завгодно (з 1С — як є): на
            // темному тлі текст мусить стати світлим, інакше картку не прочитати.
            const [r, g, bl] = [1, 3, 5].map((i) => parseInt(b.color.slice(i, i + 2), 16));
            const light = (0.299 * r + 0.587 * g + 0.114 * bl) > 150;
            fill = `background:${b.color}; color:${light ? "#1c2536" : "#ffffff"};`;
        }
        return `top:${b.top}%; height:${b.height}%; border-left-color:${edge}; ${fill}`;
    }

    goTo(iso) {
        this.state.date = iso;
        this.load();
    }
    prevDay() {
        this.goTo(DateTime.fromISO(this.state.date).minus({ days: 1 }).toISODate());
    }
    nextDay() {
        this.goTo(DateTime.fromISO(this.state.date).plus({ days: 1 }).toISODate());
    }
    today() {
        this.goTo(DateTime.local().toISODate());
    }
    onDate(ev) {
        this.goTo(ev.target.value);
    }
    get dateLabel() {
        // MMMM, а не LLLL: місяць у даті — у відмінку («30 вересня»), а не
        // окремою назвою («30 Вересень»), як слов'янські мови й вимагають.
        return DateTime.fromISO(this.state.date).toFormat("cccc, d MMMM yyyy");
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

    /** Клік у вільне місце колонки — новий запис на цей пост і цей час.
     *
     * Так у 1С: вільна клітинка розкладу — це «+ 10:15», і запис
     * народжується вже з постом і часом. Час округлюємо до 15 хвилин —
     * крок шкали 1С.
     */
    newBooking(ev, postId) {
        if (ev.target.closest(".adealer-board__event")) {
            return;
        }
        const lane = ev.currentTarget.getBoundingClientRect();
        const share = Math.min(Math.max((ev.clientY - lane.top) / lane.height, 0), 1);
        const minutes = Math.round((share * (this.state.dayEnd - this.state.dayStart) * 60)
                                   / SLOT_MINUTES) * SLOT_MINUTES;
        const at = DateTime.fromISO(this.state.date).startOf("day")
            .plus({ hours: this.state.dayStart, minutes });
        const context = {
            default_appointment_datetime: at.toUTC().toFormat("yyyy-MM-dd HH:mm:ss"),
        };
        if (postId) {
            context.default_workplace_id = postId;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "adealer.service.booking",
            views: [[false, "form"]],
            target: "current",
            context,
        });
    }

    toPeriods() {
        this.action.doAction("adealer.action_service_bookings");
    }
}

registry.category("actions").add("adealer_booking_board", AdealerBookingBoard);

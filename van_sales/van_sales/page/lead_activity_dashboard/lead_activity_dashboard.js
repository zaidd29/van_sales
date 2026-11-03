frappe.pages["lead-activity-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Lead Activity Dashboard"),
		single_column: true,
	});
	wrapper.dashboard = new FieldSalesDashboard(page);
};

frappe.pages["lead-activity-dashboard"].on_page_show = function (wrapper) {
	wrapper.dashboard && wrapper.dashboard.refresh();
};

const OUTCOME_COLORS = {
	Interested: "#2490EF",
	Converted: "#29CD42",
	"Call Back": "#ECAD4B",
	"Not Available": "#98A1A9",
	"Not Interested": "#E24C4C",
};

class FieldSalesDashboard {
	constructor(page) {
		this.page = page;
		this.make_filters();
		this.page.set_primary_action(__("Refresh"), () => this.refresh(), "refresh");
		this.page.add_inner_button(__("Activity Report"), () =>
			frappe.set_route("query-report", "Sales Person Lead Activity", {
				from_date: this.from_date.get_value(),
				to_date: this.to_date.get_value(),
			})
		);
		this.page.add_inner_button(__("All Visits"), () => frappe.set_route("List", "Lead Visit"));
		this.page.add_inner_button(__("Mobile App"), () => window.open("/van_sales", "_blank"));

		this.$body = $(`<div class="fs-dash"></div>`).appendTo(this.page.main);
		this.add_styles();
	}

	make_filters() {
		this.from_date = this.page.add_field({
			fieldname: "from_date",
			label: __("From"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -13),
			change: () => this.refresh(),
		});
		this.to_date = this.page.add_field({
			fieldname: "to_date",
			label: __("To"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			change: () => this.refresh(),
		});
		this.sales_person = this.page.add_field({
			fieldname: "sales_person",
			label: __("Sales Person"),
			fieldtype: "Link",
			options: "Sales Person",
			get_query: () => ({ filters: { is_group: 0 } }),
			change: () => this.refresh(),
		});
	}

	refresh() {
		const args = {
			from_date: this.from_date.get_value(),
			to_date: this.to_date.get_value(),
			sales_person: this.sales_person.get_value(),
		};
		const key = JSON.stringify(args);
		if (this.loading === key) return;
		this.loading = key;

		frappe.call({ method: "van_sales.api.lead_activity.get_dashboard_data", args }).then(
			(r) => {
				this.loading = null;
				this.render(r.message);
			},
			() => (this.loading = null)
		);
	}

	render(data) {
		this.data = data;
		const c = data.cards;
		const card = (label, value, color, hint) => `
			<div class="fs-card">
				<div class="fs-card-label">${label}</div>
				<div class="fs-card-value" style="color:${color}">${value}</div>
				<div class="fs-card-hint">${hint || ""}</div>
			</div>`;
		const rate = c.planned ? Math.round((100 * c.completed) / c.planned) : 0;

		this.$body.html(`
			<div class="fs-cards">
				${card(__("Open Leads Assigned"), c.leads_assigned, "var(--text-color)", __("across sales persons"))}
				${card(__("Visits Planned"), c.planned, "var(--text-color)", __("incl. unplanned"))}
				${card(__("Visits Completed"), c.completed, "#29CD42", __("{0}% completion", [rate]))}
				${card(__("Visits Missed"), c.missed, "#E24C4C", __("planned, not visited"))}
				${card(__("Out of Range"), c.out_of_range, "#ECAD4B", __("check-in far from lead"))}
				${card(__("Leads Converted"), c.converted, "#2490EF", __("outcome Converted"))}
			</div>

			<div class="fs-section">
				<div class="fs-section-title">${__("Lead Activity by Sales Person")}</div>
				<div class="fs-table-wrap">${this.people_table(data.people)}</div>
			</div>

			<div class="fs-grid">
				<div class="fs-section"><div class="fs-section-title">${__("Completed vs Missed by Sales Person")}</div><div class="fs-chart-people"></div></div>
				<div class="fs-section"><div class="fs-section-title">${__("Visit Outcomes")}</div><div class="fs-chart-outcomes"></div></div>
			</div>

			<div class="fs-section">
				<div class="fs-section-title">${__("Visits per Day")}</div>
				<div class="fs-chart-days"></div>
			</div>

			<div class="fs-grid">
				<div class="fs-section">
					<div class="fs-section-title">${__("Check-in Map")}
						<span class="fs-legend">
							<span><i style="background:#29CD42"></i>${__("In range")}</span>
							<span><i style="background:#E24C4C"></i>${__("Out of range")}</span>
						</span>
					</div>
					<div class="fs-map"></div>
				</div>
				<div class="fs-section">
					<div class="fs-section-title">${__("Latest Visit Notes")}</div>
					<div class="fs-feed">${this.feed(data.recent)}</div>
				</div>
			</div>
		`);

		this.$body.find(".fs-person-link").on("click", (e) => {
			this.sales_person.set_value($(e.currentTarget).data("person"));
		});

		this.render_charts(data);
		this.render_map(data.points);
	}

	people_table(people) {
		if (!people.length) {
			return `<div class="fs-empty">${__("No visits in this period.")}</div>`;
		}
		const esc = frappe.utils.escape_html;
		const rows = people
			.map((p) => {
				const bar = `<div class="fs-bar"><div style="width:${p.completion}%"></div></div>`;
				return `<tr>
					<td><a class="fs-person-link" data-person="${esc(p.sales_person)}">${esc(p.sales_person)}</a></td>
					<td class="num">${p.leads_assigned}</td>
					<td class="num">${p.total_visits}</td>
					<td class="num">${p.completed}</td>
					<td class="num">${p.missed}</td>
					<td class="num">${p.pending}</td>
					<td>${bar}<span class="fs-pct">${p.completion}%</span></td>
					<td class="num">${p.unplanned}</td>
					<td class="num ${p.out_of_range ? "fs-warn" : ""}">${p.out_of_range}</td>
					<td class="num">${p.interested}</td>
					<td class="num">${p.converted}</td>
					<td class="num">${p.avg_duration || "-"}</td>
					<td>${p.last_activity ? frappe.datetime.comment_when(p.last_activity) : "-"}</td>
				</tr>`;
			})
			.join("");
		return `<table class="fs-table">
			<thead><tr>
				<th>${__("Sales Person")}</th><th class="num">${__("Open Leads")}</th>
				<th class="num">${__("Visits")}</th><th class="num">${__("Completed")}</th>
				<th class="num">${__("Missed")}</th><th class="num">${__("Pending")}</th>
				<th>${__("Completion")}</th><th class="num">${__("Unplanned")}</th>
				<th class="num">${__("Out of Range")}</th><th class="num">${__("Interested")}</th>
				<th class="num">${__("Converted")}</th><th class="num">${__("Avg Min")}</th>
				<th>${__("Last Check-in")}</th>
			</tr></thead>
			<tbody>${rows}</tbody>
		</table>`;
	}

	feed(recent) {
		if (!recent.length) return `<div class="fs-empty">${__("No completed visits yet.")}</div>`;
		const esc = frappe.utils.escape_html;
		return recent
			.map(
				(v) => `
			<div class="fs-feed-item">
				<div class="fs-feed-head">
					<a href="/app/lead-visit/${v.name}"><b>${esc(v.lead_name || v.lead)}</b></a>
					<span class="fs-chip" style="background:${OUTCOME_COLORS[v.outcome] || "#98A1A9"}">${esc(
					__(v.outcome || "")
				)}</span>
				</div>
				<div class="fs-feed-meta">
					${esc(v.sales_person)} · ${frappe.datetime.str_to_user(v.check_in_time)}
					· ${v.distance ?? "-"} m ${
					v.out_of_range ? `<span class="fs-warn">${__("out of range")}</span>` : ""
				}
				</div>
				<div class="fs-feed-notes">${esc(v.notes || "")}</div>
				${
					v.out_of_range_reason
						? `<div class="fs-feed-reason">${__("Reason")}: ${esc(v.out_of_range_reason)}</div>`
						: ""
				}
			</div>`
			)
			.join("");
	}

	render_charts(data) {
		if (data.people.length) {
			new frappe.Chart(this.$body.find(".fs-chart-people")[0], {
				type: "bar",
				height: 260,
				barOptions: { stacked: 1 },
				colors: ["#29CD42", "#E24C4C", "#98A1A9"],
				data: {
					labels: data.people.map((p) => p.sales_person),
					datasets: [
						{ name: __("Completed"), values: data.people.map((p) => p.completed) },
						{ name: __("Missed"), values: data.people.map((p) => p.missed) },
						{ name: __("Pending"), values: data.people.map((p) => p.pending) },
					],
				},
			});
		}

		if (data.outcomes.length) {
			// Drawn by hand: Frappe Charts clips legend labels in a half-width card.
			const total = data.outcomes.reduce((sum, o) => sum + o.count, 0);
			const color = (o) => OUTCOME_COLORS[o.outcome] || "#98A1A9";
			this.$body.find(".fs-chart-outcomes").html(`
				<div class="fs-stack">${data.outcomes
					.map((o) => `<div style="flex:${o.count};background:${color(o)}" title="${__(o.outcome)}: ${o.count}"></div>`)
					.join("")}</div>
				<div class="fs-outcomes">${data.outcomes
					.map(
						(o) => `<div class="fs-outcome">
							<i style="background:${color(o)}"></i>
							<span class="fs-outcome-name">${__(o.outcome)}</span>
							<b>${o.count}</b>
							<span class="fs-pct">${Math.round((100 * o.count) / total)}%</span>
						</div>`
					)
					.join("")}</div>`);
		} else {
			this.$body.find(".fs-chart-outcomes").html(`<div class="fs-empty">${__("No outcomes yet.")}</div>`);
		}

		new frappe.Chart(this.$body.find(".fs-chart-days")[0], {
			type: "line",
			height: 240,
			colors: ["#98A1A9", "#29CD42", "#E24C4C"],
			lineOptions: { regionFill: 0, dotSize: 4 },
			axisOptions: { xIsSeries: 1 },
			data: {
				labels: data.days.map((d) => frappe.datetime.str_to_user(d.day).slice(0, 5)),
				datasets: [
					{ name: __("Planned"), values: data.days.map((d) => d.planned) },
					{ name: __("Completed"), values: data.days.map((d) => d.completed) },
					{ name: __("Missed"), values: data.days.map((d) => d.missed) },
				],
			},
		});
	}

	render_map(points) {
		const el = this.$body.find(".fs-map")[0];
		if (this.map) {
			this.map.remove();
			this.map = null;
		}
		if (!points.length) {
			$(el).html(`<div class="fs-empty">${__("No check-ins with a location in this period.")}</div>`);
			return;
		}
		const defaults = frappe.utils.map_defaults;
		this.map = L.map(el);
		L.tileLayer(defaults.tiles, defaults.options).addTo(this.map);

		const esc = frappe.utils.escape_html;
		const markers = points.map((p) =>
			L.circleMarker([p.lat, p.lng], {
				radius: 7,
				weight: 2,
				color: "#fff",
				fillColor: p.out_of_range ? "#E24C4C" : "#29CD42",
				fillOpacity: 0.9,
			}).bindPopup(
				`<b>${esc(p.lead_name || p.lead)}</b><br>${esc(p.sales_person)}<br>
				${frappe.datetime.str_to_user(p.check_in_time)}<br>
				${esc(__(p.outcome || p.status))} · ${p.distance ?? "-"} m<br>
				<a href="/app/lead-visit/${p.name}">${p.name}</a>`
			)
		);
		const group = L.featureGroup(markers).addTo(this.map);
		this.map.fitBounds(group.getBounds().pad(0.15));
		setTimeout(() => this.map && this.map.invalidateSize(), 200);
	}

	add_styles() {
		if (document.getElementById("fs-dash-style")) return;
		$(`<style id="fs-dash-style">
			.fs-dash { padding: 4px 0 40px; }
			.fs-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 16px; }
			.fs-card, .fs-section { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: var(--border-radius-lg); }
			.fs-card { padding: 14px 16px; }
			.fs-card-label { font-size: var(--text-sm); color: var(--text-muted); }
			.fs-card-value { font-size: 28px; font-weight: 600; line-height: 1.3; }
			.fs-card-hint { font-size: var(--text-xs); color: var(--text-light); }
			.fs-section { padding: 14px 16px; margin-bottom: 16px; min-width: 0; }
			.fs-section-title { font-weight: 600; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; gap: 8px; }
			.fs-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }
			.fs-grid .fs-section { margin-bottom: 0; }
			.fs-grid + .fs-section, .fs-section + .fs-grid { margin-top: 0; }
			.fs-grid { margin-bottom: 16px; }
			.fs-table-wrap { overflow-x: auto; }
			.fs-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
			.fs-table th { color: var(--text-muted); font-weight: 500; text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border-color); white-space: nowrap; }
			.fs-table td { padding: 8px; border-bottom: 1px solid var(--border-color); white-space: nowrap; }
			.fs-table .num { text-align: right; }
			.fs-person-link { cursor: pointer; font-weight: 500; }
			.fs-bar { display: inline-block; width: 70px; height: 6px; background: var(--gray-200); border-radius: 3px; vertical-align: middle; margin-right: 6px; overflow: hidden; }
			.fs-bar div { height: 100%; background: #29CD42; }
			.fs-pct { font-size: var(--text-xs); color: var(--text-muted); }
			.fs-warn { color: #E24C4C; font-weight: 600; }
			.fs-map { height: 380px; border-radius: var(--border-radius); z-index: 0; }
			.fs-legend { font-weight: 400; font-size: var(--text-xs); color: var(--text-muted); display: flex; gap: 10px; }
			.fs-legend i { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; }
			.fs-feed { max-height: 380px; overflow-y: auto; }
			.fs-feed-item { padding: 10px 0; border-bottom: 1px solid var(--border-color); }
			.fs-feed-item:last-child { border-bottom: 0; }
			.fs-feed-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
			.fs-feed-meta { font-size: var(--text-xs); color: var(--text-muted); margin: 2px 0 4px; }
			.fs-feed-notes { font-size: var(--text-sm); }
			.fs-feed-reason { font-size: var(--text-xs); color: #E24C4C; margin-top: 2px; }
			.fs-chip { color: #fff; font-size: 11px; padding: 1px 8px; border-radius: 10px; white-space: nowrap; }
			.fs-empty { color: var(--text-muted); padding: 24px 0; text-align: center; }
			.fs-stack { display: flex; height: 14px; border-radius: 7px; overflow: hidden; gap: 2px; margin: 18px 0 18px; }
			.fs-outcomes { display: flex; flex-direction: column; gap: 10px; }
			.fs-outcome { display: grid; grid-template-columns: 12px 1fr 48px 44px; align-items: center; gap: 10px; font-size: var(--text-md); }
			.fs-outcome i { width: 10px; height: 10px; border-radius: 3px; }
			.fs-outcome b { text-align: right; }
			.fs-outcome .fs-pct { text-align: right; }
		</style>`).appendTo("head");
	}
}

frappe.ui.form.on("Lead", {
	refresh(frm) {
		if (frm.is_new()) return;

		frm.add_custom_button(
			__("Plan Visit"),
			() => {
				const d = new frappe.ui.Dialog({
					title: __("Plan Visit to {0}", [frm.doc.lead_name]),
					fields: [
						{
							fieldname: "sales_person",
							fieldtype: "Link",
							options: "Sales Person",
							label: __("Sales Person"),
							reqd: 1,
							filters: { is_group: 0, enabled: 1 },
						},
						{
							fieldname: "planned_on",
							fieldtype: "Datetime",
							label: __("Planned On"),
							reqd: 1,
						},
						{ fieldname: "purpose", fieldtype: "Small Text", label: __("Purpose") },
					],
					primary_action_label: __("Plan"),
					primary_action(values) {
						frappe
							.call("van_sales.api.visits.plan_visit", { lead: frm.doc.name, ...values })
							.then((r) => {
								d.hide();
								frappe.show_alert({
									message: __("Visit {0} planned", [r.message]),
									indicator: "green",
								});
								frm.reload_doc();
							});
					},
				});
				frappe.call("van_sales.api.visits.get_my_sales_person").then((r) => {
					if (r.message) d.set_value("sales_person", r.message);
				});
				d.show();
			},
			__("Lead Visits")
		);

		frm.add_custom_button(
			__("Visit History"),
			() => frappe.set_route("List", "Lead Visit", { lead: frm.doc.name }),
			__("Lead Visits")
		);

		if (frm.doc.van_latitude && frm.doc.van_longitude) {
			frm.add_custom_button(
				__("Open in Google Maps"),
				() =>
					window.open(
						`https://www.google.com/maps?q=${frm.doc.van_latitude},${frm.doc.van_longitude}`,
						"_blank"
					),
				__("Lead Visits")
			);

			// A pin taken from a poor GPS fix makes every later visit look out
			// of range; clearing it lets the next good check-in pin it again.
			frm.add_custom_button(
				__("Reset Visit Location"),
				() =>
					frappe.confirm(
						__("Clear this lead's map location? The next check-in with a clear GPS signal will pin it again."),
						() => {
							frm.set_value({ van_latitude: null, van_longitude: null });
							frm.save();
						}
					),
				__("Lead Visits")
			);
		}
	},
});

frappe.ui.form.on("Lead Visit", {
	refresh(frm) {
		const colors = {
			Planned: "blue",
			"Checked In": "orange",
			Completed: "green",
			Missed: "red",
			Cancelled: "gray",
		};
		frm.page.set_indicator(__(frm.doc.status), colors[frm.doc.status] || "gray");

		if (frm.doc.out_of_range) {
			frm.dashboard.set_headline_alert(
				__("Checked in {0} m from the lead's location.", [
					Math.round(frm.doc.distance_from_lead),
				]),
				"red"
			);
		}

		if (!frm.is_new() && ["Planned", "Checked In"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Open in Van Sales App"), () => {
				window.open(`/van_sales/visit/${encodeURIComponent(frm.doc.name)}`, "_blank");
			});
		}

		if (!frm.is_new() && frm.doc.status === "Planned") {
			frm.add_custom_button(__("Cancel Visit"), () => {
				frappe.confirm(__("Cancel this planned visit?"), () => {
					frappe
						.call("van_sales.api.visits.cancel_visit", { visit: frm.doc.name })
						.then(() => frm.reload_doc());
				});
			});
		}

		if (frm.doc.check_in_latitude && frm.doc.check_in_longitude) {
			frm.add_custom_button(__("View on Google Maps"), () => {
				window.open(
					`https://www.google.com/maps?q=${frm.doc.check_in_latitude},${frm.doc.check_in_longitude}`,
					"_blank"
				);
			});
		}
	},

	onload(frm) {
		if (frm.is_new() && !frm.doc.sales_person) {
			frappe.call("van_sales.api.visits.get_my_sales_person").then((r) => {
				if (r.message) frm.set_value("sales_person", r.message);
			});
		}
	},
});

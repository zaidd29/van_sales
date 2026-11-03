frappe.listview_settings["Lead Visit"] = {
	add_fields: ["status", "out_of_range"],
	get_indicator(doc) {
		const colors = {
			Planned: "blue",
			"Checked In": "orange",
			Completed: "green",
			Missed: "red",
			Cancelled: "gray",
		};
		if (doc.status === "Completed" && doc.out_of_range) {
			return [__("Out of Range"), "red", "out_of_range,=,1"];
		}
		return [__(doc.status), colors[doc.status] || "gray", `status,=,${doc.status}`];
	},
};

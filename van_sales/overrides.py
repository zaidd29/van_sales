from frappe import _


def lead_dashboard(data):
	data.setdefault("non_standard_fieldnames", {})
	data.setdefault("transactions", [])
	data["transactions"].insert(0, {"label": _("Lead Visits"), "items": ["Lead Visit"]})
	return data

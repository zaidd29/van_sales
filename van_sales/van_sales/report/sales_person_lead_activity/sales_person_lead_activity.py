from frappe import _

from van_sales.api.lead_activity import get_sales_person_rows


def execute(filters=None):
	filters = filters or {}
	rows = get_sales_person_rows(filters.get("from_date"), filters.get("to_date"), filters.get("sales_person"))

	columns = [
		{"label": _("Sales Person"), "fieldname": "sales_person", "fieldtype": "Link", "options": "Sales Person", "width": 180},
		{"label": _("Open Leads Assigned"), "fieldname": "leads_assigned", "fieldtype": "Int", "width": 120},
		{"label": _("Visits"), "fieldname": "total_visits", "fieldtype": "Int", "width": 80},
		{"label": _("Completed"), "fieldname": "completed", "fieldtype": "Int", "width": 100},
		{"label": _("Missed"), "fieldname": "missed", "fieldtype": "Int", "width": 80},
		{"label": _("Pending"), "fieldname": "pending", "fieldtype": "Int", "width": 80},
		{"label": _("Completion %"), "fieldname": "completion", "fieldtype": "Percent", "precision": 1, "width": 110},
		{"label": _("Unplanned"), "fieldname": "unplanned", "fieldtype": "Int", "width": 90},
		{"label": _("Out of Range"), "fieldname": "out_of_range", "fieldtype": "Int", "width": 100},
		{"label": _("Leads Visited"), "fieldname": "leads_visited", "fieldtype": "Int", "width": 100},
		{"label": _("Interested"), "fieldname": "interested", "fieldtype": "Int", "width": 90},
		{"label": _("Converted"), "fieldname": "converted", "fieldtype": "Int", "width": 90},
		{"label": _("Avg. Visit (min)"), "fieldname": "avg_duration", "fieldtype": "Float", "precision": 0, "width": 110},
		{"label": _("Last Activity"), "fieldname": "last_activity", "fieldtype": "Datetime", "width": 160},
	]

	chart = {
		"data": {
			"labels": [r.sales_person for r in rows],
			"datasets": [
				{"name": _("Completed"), "values": [r.completed for r in rows]},
				{"name": _("Missed"), "values": [r.missed for r in rows]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
		"colors": ["#29CD42", "#E24C4C"],
	}

	return columns, rows, None, chart

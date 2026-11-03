import frappe
from frappe.utils import add_days, get_datetime, nowdate

from van_sales.van_sales.doctype.lead_visit.lead_visit import visit_settings


def close_past_visits():
	"""Planned visits from earlier days become Missed; forgotten check-ins are closed."""
	if not visit_settings().close_past_visits:
		return

	start_of_today = f"{nowdate()} 00:00:00"

	for name in frappe.get_all(
		"Lead Visit", filters={"status": "Planned", "planned_on": ("<", start_of_today)}, pluck="name"
	):
		frappe.db.set_value("Lead Visit", name, "status", "Missed")

	for visit in frappe.get_all(
		"Lead Visit",
		filters={"status": "Checked In", "check_in_time": ("<", start_of_today)},
		fields=["name", "check_in_time"],
	):
		end_of_day = get_datetime(f"{get_datetime(visit.check_in_time).date()} 23:59:59")
		frappe.db.set_value(
			"Lead Visit",
			visit.name,
			{
				"status": "Completed",
				"auto_closed": 1,
				"check_out_time": end_of_day,
				"duration_minutes": int((end_of_day - get_datetime(visit.check_in_time)).total_seconds() / 60),
			},
		)

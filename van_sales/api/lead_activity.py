"""Sales-person-wise lead activity, for the dashboard page and the report."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate

from van_sales.permissions import visible_sales_persons

# A visit belongs to the day it happened, or to the day it was planned for
# when it never happened.
ACTIVITY_DATE = "date(coalesce(v.check_in_time, v.planned_on))"


def _scope(from_date, to_date, sales_person=None) -> tuple[str, dict]:
	conditions = [f"{ACTIVITY_DATE} between %(from_date)s and %(to_date)s", "v.status != 'Cancelled'"]
	values = {"from_date": getdate(from_date), "to_date": getdate(to_date)}

	allowed = visible_sales_persons()
	if allowed is not None:
		conditions.append("v.sales_person in %(allowed)s")
		values["allowed"] = tuple(allowed) or ("",)
	if sales_person:
		conditions.append("v.sales_person = %(sales_person)s")
		values["sales_person"] = sales_person

	return " and ".join(conditions), values


def _sales_person_users() -> dict:
	return dict(
		frappe.db.sql(
			"""
			select sp.name, e.user_id
			from `tabSales Person` sp
			join `tabEmployee` e on e.name = sp.employee
			where ifnull(e.user_id, '') != ''
			"""
		)
	)


def _open_leads_by_user() -> dict:
	return dict(
		frappe.db.sql(
			"""
			select lead_owner, count(*) from `tabLead`
			where status not in ('Converted', 'Do Not Contact') and ifnull(lead_owner, '') != ''
			group by lead_owner
			"""
		)
	)


def get_sales_person_rows(from_date, to_date, sales_person=None) -> list[dict]:
	where, values = _scope(from_date, to_date, sales_person)
	rows = frappe.db.sql(
		f"""
		select
			v.sales_person,
			count(*) as total_visits,
			sum(v.status = 'Completed') as completed,
			sum(v.status = 'Missed') as missed,
			sum(v.status in ('Planned', 'Checked In')) as pending,
			sum(v.visit_type = 'Unplanned') as unplanned,
			sum(v.status = 'Completed' and v.out_of_range = 1) as out_of_range,
			sum(v.outcome = 'Interested') as interested,
			sum(v.outcome = 'Converted') as converted,
			count(distinct case when v.status = 'Completed' then v.lead end) as leads_visited,
			avg(case when v.status = 'Completed' and v.auto_closed = 0 then v.duration_minutes end) as avg_duration,
			max(v.check_in_time) as last_activity
		from `tabLead Visit` v
		where {where}
		group by v.sales_person
		order by completed desc, v.sales_person
		""",
		values,
		as_dict=True,
	)

	users = _sales_person_users()
	open_leads = _open_leads_by_user()
	for row in rows:
		for key in ("completed", "missed", "pending", "unplanned", "out_of_range", "interested", "converted"):
			row[key] = cint(row[key])
		row.leads_assigned = cint(open_leads.get(users.get(row.sales_person)))
		row.avg_duration = flt(row.avg_duration, 0)
		row.completion = flt(100.0 * row.completed / row.total_visits, 1) if row.total_visits else 0
	return rows


@frappe.whitelist()
def get_dashboard_data(from_date=None, to_date=None, sales_person=None):
	to_date = getdate(to_date or nowdate())
	from_date = getdate(from_date or add_days(to_date, -13))
	where, values = _scope(from_date, to_date, sales_person)

	people = get_sales_person_rows(from_date, to_date, sales_person)

	daily = frappe.db.sql(
		f"""
		select {ACTIVITY_DATE} as day,
			count(*) as planned,
			sum(v.status = 'Completed') as completed,
			sum(v.status = 'Missed') as missed
		from `tabLead Visit` v
		where {where}
		group by day order by day
		""",
		values,
		as_dict=True,
	)
	by_day = {str(row.day): row for row in daily}
	days, day = [], from_date
	while day <= to_date:
		row = by_day.get(str(day)) or {}
		days.append(
			{
				"day": str(day),
				"planned": cint(row.get("planned")),
				"completed": cint(row.get("completed")),
				"missed": cint(row.get("missed")),
			}
		)
		day = add_days(day, 1)

	outcomes = frappe.db.sql(
		f"""
		select v.outcome, count(*) as count
		from `tabLead Visit` v
		where {where} and v.status = 'Completed' and ifnull(v.outcome, '') != ''
		group by v.outcome order by count desc
		""",
		values,
		as_dict=True,
	)

	points = frappe.db.sql(
		f"""
		select v.name, v.lead, v.lead_name, v.sales_person, v.outcome, v.status, v.check_in_time,
			v.check_in_latitude as lat, v.check_in_longitude as lng, v.out_of_range,
			round(v.distance_from_lead) as distance
		from `tabLead Visit` v
		where {where} and v.check_in_latitude is not null and v.check_in_latitude != 0
		order by v.check_in_time desc
		limit 500
		""",
		values,
		as_dict=True,
	)

	recent = frappe.db.sql(
		f"""
		select v.name, v.lead, v.lead_name, v.company_name, v.sales_person, v.outcome, v.notes,
			v.check_in_time, round(v.distance_from_lead) as distance, v.out_of_range,
			v.out_of_range_reason, v.duration_minutes
		from `tabLead Visit` v
		where {where} and v.status = 'Completed'
		order by v.check_in_time desc
		limit 25
		""",
		values,
		as_dict=True,
	)

	allowed = visible_sales_persons()
	sp_filters = {"is_group": 0, "enabled": 1}
	if allowed is not None:
		sp_filters["name"] = ("in", allowed or [""])

	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"cards": {
			"leads_assigned": sum(r.leads_assigned for r in people),
			"planned": sum(r.total_visits for r in people),
			"completed": sum(r.completed for r in people),
			"missed": sum(r.missed for r in people),
			"out_of_range": sum(r.out_of_range for r in people),
			"converted": sum(r.converted for r in people),
		},
		"people": people,
		"days": days,
		"outcomes": outcomes,
		"points": points,
		"recent": recent,
		"sales_persons": frappe.get_all("Sales Person", filters=sp_filters, pluck="name", order_by="name"),
		"labels": {"title": _("Lead Activity Dashboard")},
	}

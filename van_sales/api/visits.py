"""Lead visits: plan a visit, check in where the lead is, check out with notes.

A visit belongs to a Sales Person, found from the signed-in user through
their Employee record -- the same link ERPNext uses for sales team
commission, so no second mapping has to be kept up to date. Check-in
carries the device's position and is measured against the lead's pinned
location; a check-in outside the allowed radius is accepted but flagged,
and the rep has to say why before they can check out.
"""

import math
import random

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime, nowdate

from van_sales.permissions import get_sales_person, is_manager, visible_sales_persons
from van_sales.van_sales.doctype.lead_visit.lead_visit import visit_settings

VISIT_FIELDS = [
	"name",
	"lead",
	"lead_name",
	"company_name",
	"mobile_no",
	"sales_person",
	"visit_type",
	"status",
	"planned_on",
	"purpose",
	"check_in_time",
	"check_out_time",
	"distance_from_lead",
	"out_of_range",
	"out_of_range_reason",
	"location_source",
	"outcome",
	"notes",
	"next_visit_on",
	"duration_minutes",
]


def _require_sales_person() -> str:
	sales_person = get_sales_person()
	if not sales_person:
		frappe.throw(
			_(
				"Your user is not linked to a Sales Person. Link your Employee record to a Sales Person and try again."
			),
			title=_("No Sales Person"),
		)
	return sales_person


def _lead_location(lead: str) -> dict:
	return frappe.db.get_value(
		"Lead",
		lead,
		["name", "lead_name", "company_name", "mobile_no", "city", "van_latitude", "van_longitude"],
		as_dict=True,
	)


def _with_lead_location(visits: list[dict]) -> list[dict]:
	leads = {v.lead for v in visits}
	if not leads:
		return visits
	locations = {
		row.name: row
		for row in frappe.get_all(
			"Lead",
			filters={"name": ("in", list(leads))},
			fields=["name", "city", "van_latitude", "van_longitude"],
		)
	}
	for visit in visits:
		loc = locations.get(visit.lead) or {}
		visit.city = loc.get("city")
		visit.lead_latitude = loc.get("van_latitude")
		visit.lead_longitude = loc.get("van_longitude")
	return visits


def _get_visit_for_update(name: str):
	doc = frappe.get_doc("Lead Visit", name)
	doc.check_permission("write")
	return doc


@frappe.whitelist()
def get_my_sales_person():
	return get_sales_person()


@frappe.whitelist()
def get_my_day():
	"""Everything the app's Today screen shows."""
	sales_person = _require_sales_person()
	today = getdate(nowdate())

	visits = frappe.get_all(
		"Lead Visit",
		filters={
			"sales_person": sales_person,
			"status": ("!=", "Cancelled"),
			"planned_on": ("between", [f"{today} 00:00:00", f"{today} 23:59:59"]),
		},
		fields=VISIT_FIELDS,
		order_by="planned_on asc",
	)
	# Unplanned visits started today have no planned time, but belong on today.
	unplanned = frappe.get_all(
		"Lead Visit",
		filters={
			"sales_person": sales_person,
			"planned_on": ("is", "not set"),
			"check_in_time": ("between", [f"{today} 00:00:00", f"{today} 23:59:59"]),
		},
		fields=VISIT_FIELDS,
	)
	visits = _with_lead_location(visits + unplanned)

	active = frappe.get_all(
		"Lead Visit",
		filters={"sales_person": sales_person, "status": "Checked In"},
		fields=VISIT_FIELDS,
		limit=1,
	)
	settings = visit_settings()

	return {
		"user": frappe.session.user,
		"full_name": frappe.utils.get_fullname(frappe.session.user),
		"sales_person": sales_person,
		"today": str(today),
		"settings": {
			"allowed_radius": settings.allowed_radius,
			"allow_simulated_location": settings.allow_simulated_location,
			"notes_mandatory": settings.notes_mandatory,
		},
		"visits": visits,
		"active_visit": _with_lead_location(active)[0] if active else None,
		"stats": {
			"planned": len(visits),
			"completed": sum(1 for v in visits if v.status == "Completed"),
			"pending": sum(1 for v in visits if v.status in ("Planned", "Checked In")),
			"out_of_range": sum(1 for v in visits if v.out_of_range),
		},
	}


@frappe.whitelist()
def get_my_leads(search: str | None = None):
	"""Open leads owned by or assigned to the current user.

	A manager plans visits for the whole team, so they get every open lead.
	"""
	user = frappe.session.user
	conditions = ["status not in ('Converted', 'Do Not Contact')"]
	values = {"user": user, "assign": f'%"{user}"%'}
	if not is_manager(user):
		conditions.append("(lead_owner = %(user)s or _assign like %(assign)s)")
	if search:
		conditions.append("(lead_name like %(search)s or company_name like %(search)s or city like %(search)s)")
		values["search"] = f"%{search}%"

	leads = frappe.db.sql(
		f"""
		select name, lead_name, company_name, mobile_no, city, status, lead_owner,
			van_latitude, van_longitude, van_last_visit_on, van_last_visit_outcome, van_visit_count
		from `tabLead`
		where {" and ".join(conditions)}
		order by coalesce(van_last_visit_on, creation) desc
		limit 200
		""",
		values,
		as_dict=True,
	)

	upcoming = {
		row.lead: row
		for row in frappe.get_all(
			"Lead Visit",
			filters={
				"lead": ("in", [lead.name for lead in leads] or [""]),
				"status": "Planned",
				"planned_on": (">=", nowdate()),
			},
			fields=["lead", "name", "planned_on"],
			order_by="planned_on desc",
		)
	}
	for lead in leads:
		nxt = upcoming.get(lead.name)
		lead.next_visit = nxt.planned_on if nxt else None
		lead.next_visit_name = nxt.name if nxt else None
	return leads


@frappe.whitelist()
def get_visit(name: str):
	"""One visit with the lead's pinned location, for the visit screen."""
	doc = frappe.get_doc("Lead Visit", name)
	doc.check_permission("read")
	visit = frappe._dict({f: doc.get(f) for f in VISIT_FIELDS})
	visit.update(
		{
			"check_in_latitude": doc.check_in_latitude,
			"check_in_longitude": doc.check_in_longitude,
			"auto_closed": doc.auto_closed,
			"previous_visit": doc.previous_visit,
			"followup_visit": doc.followup_visit,
			"is_mine": doc.sales_person == get_sales_person(),
		}
	)
	return _with_lead_location([visit])[0]


@frappe.whitelist()
def get_team():
	"""Sales persons the current user may plan visits for."""
	allowed = visible_sales_persons()
	filters = {"is_group": 0, "enabled": 1}
	if allowed is not None:
		filters["name"] = ("in", allowed or [""])
	return {
		"mine": get_sales_person(),
		"sales_persons": frappe.get_all("Sales Person", filters=filters, pluck="name", order_by="name"),
	}


@frappe.whitelist()
def get_my_history(limit: int = 30):
	sales_person = _require_sales_person()
	visits = frappe.get_all(
		"Lead Visit",
		filters={"sales_person": sales_person, "status": ("in", ["Completed", "Missed"])},
		fields=VISIT_FIELDS,
		order_by="coalesce(check_in_time, planned_on) desc",
		limit=cint(limit) or 30,
	)
	return visits


@frappe.whitelist(methods=["POST"])
def plan_visit(lead: str, planned_on: str, purpose: str | None = None, sales_person: str | None = None):
	sales_person = sales_person or _require_sales_person()
	allowed = visible_sales_persons()
	if allowed is not None and sales_person not in allowed:
		frappe.throw(_("You cannot plan visits for {0}.").format(sales_person), frappe.PermissionError)
	if frappe.db.get_value("Sales Person", sales_person, "is_group"):
		# A manager's own Sales Person is usually the team's group node.
		frappe.throw(_("{0} is a sales team, not a person. Choose who will visit.").format(sales_person))
	if get_datetime(planned_on) < get_datetime(nowdate()):
		frappe.throw(_("A visit cannot be planned in the past."))

	doc = frappe.get_doc(
		{
			"doctype": "Lead Visit",
			"lead": lead,
			"sales_person": sales_person,
			"visit_type": "Planned",
			"planned_on": planned_on,
			"purpose": purpose,
		}
	).insert()
	return doc.name


def _simulated_point(lead: dict) -> tuple[float, float]:
	"""A point 20-120 m from the lead, for demos where the device has no GPS fix."""
	if not (lead.van_latitude and lead.van_longitude):
		frappe.throw(_("Lead {0} has no map location to simulate a check-in at.").format(lead.lead_name))
	distance = random.uniform(20, 120)
	bearing = random.uniform(0, 2 * math.pi)
	d_lat = (distance * math.cos(bearing)) / 111320
	d_lng = (distance * math.sin(bearing)) / (111320 * math.cos(math.radians(flt(lead.van_latitude))))
	return flt(lead.van_latitude) + d_lat, flt(lead.van_longitude) + d_lng


@frappe.whitelist(methods=["POST"])
def check_in(
	lead: str | None = None,
	visit: str | None = None,
	latitude: float | None = None,
	longitude: float | None = None,
	accuracy: float | None = None,
	simulated: int = 0,
):
	"""Check in to a planned visit, or start an unplanned one on `lead`."""
	sales_person = _require_sales_person()

	open_visit = frappe.db.get_value(
		"Lead Visit", {"sales_person": sales_person, "status": "Checked In"}, ["name", "lead_name"], as_dict=True
	)
	if open_visit and open_visit.name != visit:
		frappe.throw(
			_("You are still checked in at {0}. Check out there first.").format(open_visit.lead_name),
			title=_("Visit in Progress"),
		)

	if visit:
		doc = _get_visit_for_update(visit)
	else:
		if not lead:
			frappe.throw(_("Choose a lead to visit."))
		doc = frappe.get_doc(
			{
				"doctype": "Lead Visit",
				"lead": lead,
				"sales_person": sales_person,
				"visit_type": "Unplanned",
			}
		)
		doc.insert()

	simulated = cint(simulated)
	if simulated:
		if not visit_settings().allow_simulated_location:
			frappe.throw(
				_("Location is required to check in. Allow location access on your phone and try again.")
			)
		latitude, longitude = _simulated_point(_lead_location(doc.lead))
		accuracy = 0
	elif latitude in (None, "") or longitude in (None, ""):
		frappe.throw(_("Location is required to check in. Allow location access on your phone and try again."))

	doc.check_in(flt(latitude), flt(longitude), accuracy, simulated=bool(simulated))
	return _with_lead_location([frappe._dict({f: doc.get(f) for f in VISIT_FIELDS})])[0]


@frappe.whitelist(methods=["POST"])
def check_out(
	visit: str,
	outcome: str,
	notes: str | None = None,
	latitude: float | None = None,
	longitude: float | None = None,
	next_visit_on: str | None = None,
	out_of_range_reason: str | None = None,
):
	doc = _get_visit_for_update(visit)
	doc.check_out(
		outcome=outcome,
		notes=notes,
		latitude=flt(latitude) if latitude not in (None, "") else None,
		longitude=flt(longitude) if longitude not in (None, "") else None,
		next_visit_on=next_visit_on or None,
		out_of_range_reason=out_of_range_reason,
	)
	return {"name": doc.name, "followup_visit": doc.followup_visit, "duration_minutes": doc.duration_minutes}


@frappe.whitelist(methods=["POST"])
def cancel_visit(visit: str):
	doc = _get_visit_for_update(visit)
	if doc.status != "Planned":
		frappe.throw(_("Only planned visits can be cancelled."))
	doc.status = "Cancelled"
	doc.save()
	return doc.name

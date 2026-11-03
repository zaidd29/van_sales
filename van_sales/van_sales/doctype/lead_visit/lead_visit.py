# Copyright (c) 2026, Matiyas Solutions LLP and contributors
# For license information, please see license.txt

import json
import math

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime, now_datetime, time_diff_in_seconds

from van_sales.api.utils import setting

LEAD_STATUS_FOR_OUTCOME = {
	"Interested": "Interested",
	"Converted": "Opportunity",
	"Call Back": "Open",
	"Not Available": "Open",
	"Not Interested": "Do Not Contact",
}

# A visit outcome may move a lead along, but never back from a status that
# ERPNext set from a real document (Quotation, Customer...).
LEAD_STATUSES_A_VISIT_MAY_CHANGE = ("Lead", "Open", "Replied", "Interested")

# The roughest fix (metres) that may pin an unmapped lead. A network-based
# fix indoors can be a kilometre off, and every later visit would be measured
# against it; the lead stays unpinned until a visit with a better fix.
MAX_PIN_ACCURACY = 100


def visit_settings() -> frappe._dict:
	"""The lead visit rules from Van Sales Settings, with their documented defaults."""
	return frappe._dict(
		allowed_radius=cint(setting("visit_allowed_radius", 200)) or 200,
		save_lead_location_on_first_visit=cint(setting("save_lead_location_on_first_visit", 1)),
		allow_simulated_location=cint(setting("allow_simulated_location", 0)),
		notes_mandatory=cint(setting("visit_notes_mandatory", 1)),
		add_notes_to_lead=cint(setting("add_visit_notes_to_lead", 1)),
		update_lead_status=cint(setting("update_lead_status_from_visit", 1)),
		close_past_visits=cint(setting("close_past_visits", 1)),
	)


def distance_in_metres(lat1, lng1, lat2, lng2) -> float:
	"""Great-circle distance between two points (haversine)."""
	radius = 6371000
	phi1, phi2 = math.radians(lat1), math.radians(lat2)
	d_phi = math.radians(lat2 - lat1)
	d_lambda = math.radians(lng2 - lng1)
	a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
	return 2 * radius * math.asin(math.sqrt(a))


def point_geojson(lat, lng, label=None) -> str:
	return json.dumps(
		{
			"type": "FeatureCollection",
			"features": [
				{
					"type": "Feature",
					"properties": {"name": label} if label else {},
					"geometry": {"type": "Point", "coordinates": [flt(lng), flt(lat)]},
				}
			],
		}
	)


class LeadVisit(Document):
	def validate(self):
		if not self.planned_on and self.visit_type == "Planned":
			self.planned_on = now_datetime()
		self.set_duration()

	def set_duration(self):
		if self.check_in_time and self.check_out_time:
			seconds = time_diff_in_seconds(self.check_out_time, self.check_in_time)
			self.duration_minutes = max(cint(seconds / 60), 0)

	def check_in(self, latitude, longitude, accuracy=None, simulated=False):
		if self.status not in ("Planned", "Missed"):
			frappe.throw(_("Visit {0} is already {1}.").format(self.name, self.status))

		settings = visit_settings()
		lead = frappe.db.get_value(
			"Lead", self.lead, ["van_latitude", "van_longitude", "lead_name"], as_dict=True
		)

		self.status = "Checked In"
		self.check_in_time = now_datetime()
		self.check_in_latitude = flt(latitude, 6)
		self.check_in_longitude = flt(longitude, 6)
		self.check_in_accuracy = flt(accuracy)
		self.location_source = "Simulated (Demo)" if simulated else "Device GPS"
		self.check_in_map = point_geojson(latitude, longitude, lead.lead_name)

		if lead.van_latitude and lead.van_longitude:
			self.distance_from_lead = distance_in_metres(
				flt(lead.van_latitude), flt(lead.van_longitude), flt(latitude), flt(longitude)
			)
			# The phone may be anywhere inside its accuracy circle, so a rep
			# standing at the lead is not flagged for GPS drift. The allowance
			# is capped at the radius: a ±2 km fix cannot prove anything.
			allowance = min(flt(accuracy), settings.allowed_radius)
			self.out_of_range = cint(self.distance_from_lead - allowance > settings.allowed_radius)
		elif (
			settings.save_lead_location_on_first_visit
			and not simulated
			and flt(accuracy) <= MAX_PIN_ACCURACY
		):
			# The first visit pins an unmapped lead, so the next one can be verified.
			frappe.db.set_value(
				"Lead",
				self.lead,
				{"van_latitude": self.check_in_latitude, "van_longitude": self.check_in_longitude},
			)
			self.distance_from_lead = 0
			self.out_of_range = 0

		self.save()

	def check_out(
		self,
		outcome,
		notes=None,
		latitude=None,
		longitude=None,
		next_visit_on=None,
		out_of_range_reason=None,
	):
		if self.status != "Checked In":
			frappe.throw(_("Check in to visit {0} before checking out.").format(self.name))

		settings = visit_settings()
		if not outcome:
			frappe.throw(_("Select the outcome of the visit."))
		if settings.notes_mandatory and not (notes or "").strip():
			frappe.throw(_("Enter notes for the visit."))
		if self.out_of_range and not (out_of_range_reason or self.out_of_range_reason or "").strip():
			frappe.throw(
				_("You checked in {0} m from the lead's location. Enter the reason.").format(
					cint(self.distance_from_lead)
				)
			)
		if next_visit_on and get_datetime(next_visit_on) <= now_datetime():
			frappe.throw(_("Next visit must be in the future."))

		self.outcome = outcome
		self.notes = notes
		if out_of_range_reason:
			self.out_of_range_reason = out_of_range_reason
		self.next_visit_on = next_visit_on or None
		self.check_out_time = now_datetime()
		if latitude is not None and longitude is not None:
			self.check_out_latitude = flt(latitude, 6)
			self.check_out_longitude = flt(longitude, 6)
		self.status = "Completed"
		self.save()

		if self.next_visit_on:
			self.create_followup()
		self.update_lead(settings)

	def create_followup(self):
		followup = frappe.get_doc(
			{
				"doctype": "Lead Visit",
				"lead": self.lead,
				"sales_person": self.sales_person,
				"visit_type": "Follow-up",
				"planned_on": self.next_visit_on,
				"purpose": _("Follow-up of {0}: {1}").format(self.name, self.outcome),
				"previous_visit": self.name,
			}
		).insert(ignore_permissions=True)
		self.db_set("followup_visit", followup.name)

	def update_lead(self, settings):
		lead = frappe.get_doc("Lead", self.lead)
		updates = {
			"van_last_visit_on": self.check_in_time,
			"van_last_visit_outcome": self.outcome,
			"van_visit_count": frappe.db.count("Lead Visit", {"lead": self.lead, "status": "Completed"}),
		}

		new_status = LEAD_STATUS_FOR_OUTCOME.get(self.outcome)
		if settings.update_lead_status and new_status and lead.status in LEAD_STATUSES_A_VISIT_MAY_CHANGE:
			updates["status"] = new_status

		frappe.db.set_value("Lead", self.lead, updates)

		if settings.add_notes_to_lead and self.notes:
			# Appended directly so a Lead that fails its own validation (a stale
			# email, say) never blocks the rep from closing a visit.
			frappe.get_doc(
				{
					"doctype": "CRM Note",
					"parent": self.lead,
					"parenttype": "Lead",
					"parentfield": "notes",
					"idx": len(lead.notes) + 1,
					"note": "<p><b>{}</b> ({}, {} m from lead)</p><p>{}</p>".format(
						frappe.utils.escape_html(self.outcome),
						frappe.utils.escape_html(self.sales_person),
						cint(self.distance_from_lead),
						frappe.utils.escape_html(self.notes).replace("\n", "<br>"),
					),
					"added_by": frappe.session.user,
					"added_on": self.check_out_time,
				}
			).db_insert()

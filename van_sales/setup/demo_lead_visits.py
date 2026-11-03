"""Demo data for showing lead visit tracking to a client.

    bench --site <site> execute van_sales.setup.demo_lead_visits.create_demo
    bench --site <site> execute van_sales.setup.demo_lead_visits.create_demo --kwargs "{'reset': 1}"

Creates a manager, four sales persons, 24 leads around Mumbai with map pins,
two weeks of visit history and today's plan. Run it with reset=1 on the
morning of a demo so "today" in the app is the demo day.
"""

import math
import random

import frappe
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime, nowdate

from van_sales.van_sales.doctype.lead_visit.lead_visit import distance_in_metres, point_geojson

PASSWORD = "Demo@1234"
DOMAIN = "fieldsales.demo"
TEAM = "Mumbai Field Team"

MANAGER = ("neha.kapoor", "Neha", "Kapoor", "Female")
REPS = [
	# (user, first, last, gender, how reliably they complete planned visits)
	("rahul.sharma", "Rahul", "Sharma", "Male", 0.95),
	("priya.nair", "Priya", "Nair", "Female", 0.90),
	("amit.patel", "Amit", "Patel", "Male", 0.80),
	("sneha.joshi", "Sneha", "Joshi", "Female", 0.65),
]

LEADS = [
	# (first, last, company, area, lat, lng)
	("Vikram", "Mehta", "Mehta Hardware Mart", "Andheri East", 19.1136, 72.8697),
	("Anjali", "Desai", "Desai Electricals", "Bandra West", 19.0596, 72.8295),
	("Rohit", "Kulkarni", "Kulkarni Office Supplies", "Powai", 19.1176, 72.9060),
	("Farhan", "Shaikh", "Shaikh Traders", "Kurla West", 19.0726, 72.8845),
	("Meera", "Iyer", "Iyer Pharma Distributors", "Chembur", 19.0522, 72.9005),
	("Karan", "Malhotra", "Malhotra Textiles", "Dadar West", 19.0178, 72.8478),
	("Sunita", "Rao", "Rao Kitchen Appliances", "Goregaon East", 19.1663, 72.8526),
	("Deepak", "Jain", "Jain Steel Works", "Malad West", 19.1874, 72.8484),
	("Pooja", "Agarwal", "Agarwal Stationers", "Borivali West", 19.2307, 72.8567),
	("Nikhil", "Verma", "Verma Auto Parts", "Thane West", 19.2183, 72.9781),
	("Ayesha", "Khan", "Khan Furnishings", "Vashi", 19.0771, 72.9986),
	("Sanjay", "Patil", "Patil Agro Foods", "Navi Mumbai, Nerul", 19.0330, 73.0297),
	("Ritu", "Bansal", "Bansal Packaging", "Lower Parel", 18.9966, 72.8295),
	("Arjun", "Reddy", "Reddy IT Solutions", "BKC", 19.0674, 72.8686),
	("Neelam", "Gupta", "Gupta Medical Store", "Ghatkopar East", 19.0790, 72.9080),
	("Harish", "Nambiar", "Nambiar Logistics", "Bhiwandi Road", 19.1960, 73.0400),
	("Kavita", "Shah", "Shah Diamonds", "Opera House", 18.9548, 72.8170),
	("Manoj", "Tiwari", "Tiwari Cold Storage", "Vikhroli", 19.1110, 72.9280),
	("Shreya", "Pillai", "Pillai Interiors", "Juhu", 19.1075, 72.8263),
	("Imran", "Qureshi", "Qureshi Leather Goods", "Dharavi", 19.0380, 72.8538),
	("Lata", "Bhosale", "Bhosale Dairy", "Mulund West", 19.1726, 72.9425),
	("Gaurav", "Chopra", "Chopra Builders", "Worli", 19.0176, 72.8162),
	("Tanvi", "Sawant", "Sawant Caterers", "Dombivli", None, None),
	("Rakesh", "Yadav", "Yadav Transport", "Kalyan", None, None),
]

NOTES = {
	"Interested": [
		"Met the owner. Wants a quotation for 50 units, decision by month end.",
		"Good meeting with purchase head. Asked for product brochure and price list on WhatsApp.",
		"Interested in annual contract. Needs approval from partner, follow up next week.",
		"Demo done, liked the features. Asked for 2 references from existing customers.",
	],
	"Converted": [
		"Order confirmed for first batch. Sent details to back office for quotation.",
		"Agreed on pricing with 5% discount. PO expected tomorrow.",
	],
	"Call Back": [
		"Owner was busy with an audit. Asked to call back on Thursday.",
		"Manager on leave this week, asked to revisit after Monday.",
		"Needs to check budget with accounts. Call back in 3 days.",
	],
	"Not Available": [
		"Shop closed for renovation. Spoke to the watchman.",
		"Contact person not in office, left visiting card at reception.",
	],
	"Not Interested": [
		"Already has a supplier on a 2-year contract. Not interested now.",
		"Price too high compared to local vendor.",
	],
}
OUTCOME_WEIGHTS = {"Interested": 35, "Call Back": 25, "Not Available": 15, "Converted": 12, "Not Interested": 13}
OUT_OF_RANGE_REASONS = [
	"Met the owner at their godown, not at the shop address.",
	"Lead address on record is old, they have moved to a new office nearby.",
	"Met at a trade fair close to their area.",
]


def _offset(lat, lng, metres):
	bearing = random.uniform(0, 2 * math.pi)
	d_lat = metres * math.cos(bearing) / 111320
	d_lng = metres * math.sin(bearing) / (111320 * math.cos(math.radians(lat)))
	return lat + d_lat, lng + d_lng


def _user(name, first, last, gender, roles):
	email = f"{name}@{DOMAIN}"
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first,
				"last_name": last,
				"gender": gender,
				"send_welcome_email": 0,
				"user_type": "System User",
				"new_password": PASSWORD,
			}
		)
		user.flags.no_welcome_mail = True
		user.insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	user.add_roles(*roles)
	return email


def _employee(email, first, last, gender, company):
	name = frappe.db.get_value("Employee", {"user_id": email})
	if name:
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": first,
				"last_name": last,
				"gender": gender,
				"date_of_birth": "1992-04-15",
				"date_of_joining": "2023-06-01",
				"company": company,
				"status": "Active",
				"user_id": email,
				"designation": None,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _sales_person(name, employee, parent, is_group=0):
	if not frappe.db.exists("Sales Person", name):
		frappe.get_doc(
			{
				"doctype": "Sales Person",
				"sales_person_name": name,
				"parent_sales_person": parent,
				"is_group": is_group,
				"employee": employee,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
	return name


def _visit(lead, sales_person, planned_on, status, visit_type="Planned", **values):
	doc = frappe.get_doc(
		{
			"doctype": "Lead Visit",
			"lead": lead.name,
			"sales_person": sales_person,
			"visit_type": visit_type,
			"planned_on": planned_on,
			"purpose": random.choice(
				["Product presentation", "Price discussion", "Collect requirements", "Follow-up on quotation", None]
			),
			"status": status,
			**values,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def _completed_values(lead, check_in, out_of_range, outcome, radius):
	if lead.van_latitude:
		lat, lng = _offset(
			lead.van_latitude, lead.van_longitude, random.uniform(700, 2600) if out_of_range else random.uniform(8, 150)
		)
		distance = distance_in_metres(lead.van_latitude, lead.van_longitude, lat, lng)
	else:
		lat, lng = 19.0 + random.uniform(0.05, 0.2), 72.85 + random.uniform(0.0, 0.15)
		distance = None
	duration = random.randint(12, 55)
	return {
		"check_in_time": check_in,
		"check_in_latitude": round(lat, 6),
		"check_in_longitude": round(lng, 6),
		"check_in_accuracy": random.randint(5, 35),
		"location_source": "Device GPS",
		"check_in_map": point_geojson(lat, lng, lead.lead_name),
		"distance_from_lead": distance,
		"out_of_range": int(bool(distance and distance > radius)),
		"out_of_range_reason": random.choice(OUT_OF_RANGE_REASONS) if distance and distance > radius else None,
		"outcome": outcome,
		"notes": random.choice(NOTES[outcome]),
		"check_out_time": add_to_date(check_in, minutes=duration),
		"check_out_latitude": round(lat, 6),
		"check_out_longitude": round(lng, 6),
	}


def _reset():
	frappe.db.delete("Lead Visit")
	leads = frappe.get_all("Lead", filters={"lead_owner": ("like", f"%@{DOMAIN}")}, pluck="name")
	if leads:
		frappe.db.delete("CRM Note", {"parenttype": "Lead", "parent": ("in", leads)})
		frappe.db.sql(
			"""update `tabLead` set van_last_visit_on = null, van_last_visit_outcome = null, van_visit_count = 0,
			status = 'Open' where name in %s""",
			(tuple(leads),),
		)


def create_demo(reset=0):
	random.seed(42)
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {})
	if not company:
		frappe.throw(
			"This site has no Company yet. Log in as Administrator and finish the ERPNext "
			"setup wizard, then run the demo again."
		)
	root = frappe.get_all("Sales Person", filters={"is_group": 1, "parent_sales_person": ("in", ["", None])}, pluck="name")
	root = root[0] if root else "Sales Team"

	# People
	m_user, m_first, m_last, m_gender = MANAGER
	manager_email = _user(m_user, m_first, m_last, m_gender, ["Field Sales Manager", "Sales Manager", "Sales User"])
	manager_emp = _employee(manager_email, m_first, m_last, m_gender, company)
	_sales_person(TEAM, manager_emp, root, is_group=1)

	reps = []
	for user, first, last, gender, reliability in REPS:
		email = _user(user, first, last, gender, ["Field Sales User", "Sales User"])
		emp = _employee(email, first, last, gender, company)
		reps.append((_sales_person(f"{first} {last}", emp, TEAM), email, reliability))

	# Leads: six per rep
	for i, (first, last, org, area, lat, lng) in enumerate(LEADS):
		if frappe.db.exists("Lead", {"company_name": org}):
			continue
		rep = reps[i % len(reps)]
		frappe.get_doc(
			{
				"doctype": "Lead",
				"first_name": first,
				"last_name": last,
				"company_name": org,
				"mobile_no": f"98{random.randint(10000000, 99999999)}",
				"city": f"{area}, Mumbai" if "Mumbai" not in area else area,
				"country": "India",
				"territory": "India",
				"source": random.choice(["Cold Calling", "Advertisement", "Reference", "Exhibition"]),
				"lead_owner": rep[1],
				"status": "Open",
				"van_latitude": lat,
				"van_longitude": lng,
			}
		).insert(ignore_permissions=True)

	frappe.db.set_single_value("Van Sales Settings", "allow_simulated_location", 1)

	if frappe.db.count("Lead Visit") and not int(reset):
		print("Visits already exist; run with reset=1 to rebuild them.")
		return
	_reset()

	radius = frappe.db.get_single_value("Van Sales Settings", "visit_allowed_radius") or 200
	today = getdate(nowdate())
	now = now_datetime()

	for sales_person, email, reliability in reps:
		leads = frappe.get_all(
			"Lead",
			filters={"lead_owner": email},
			fields=["name", "lead_name", "van_latitude", "van_longitude"],
		)

		# Two weeks of history, Monday to Saturday
		for back in range(14, 0, -1):
			day = add_days(today, -back)
			if getdate(day).weekday() == 6:
				continue
			for slot, hour in enumerate(random.sample([10, 11, 12, 14, 15, 16, 17], random.randint(2, 4))):
				lead = random.choice(leads)
				planned = get_datetime(f"{day} {hour:02d}:{random.choice(['00', '15', '30'])}:00")
				if random.random() > reliability:
					_visit(lead, sales_person, planned, "Missed")
					continue
				outcome = random.choices(list(OUTCOME_WEIGHTS), weights=list(OUTCOME_WEIGHTS.values()))[0]
				out_of_range = random.random() < (0.08 if reliability > 0.85 else 0.22)
				check_in = add_to_date(planned, minutes=random.randint(-10, 35))
				visit_type = "Unplanned" if slot == 0 and random.random() < 0.2 else "Planned"
				_visit(
					lead,
					sales_person,
					None if visit_type == "Unplanned" else planned,
					"Completed",
					visit_type,
					**_completed_values(lead, check_in, out_of_range, outcome, radius),
				)

		# Today: morning visits done (if the morning has passed), afternoon still to do
		todays = random.sample(leads, 4)
		for lead, hour in zip(todays, (10, 12, 15, 17), strict=False):
			planned = get_datetime(f"{today} {hour:02d}:00:00")
			if hour < 13 and planned < now and reliability > 0.7:
				outcome = random.choice(["Interested", "Call Back", "Converted"])
				check_in = add_to_date(planned, minutes=random.randint(0, 20))
				_visit(lead, sales_person, planned, "Completed", **_completed_values(lead, check_in, False, outcome, radius))
			else:
				_visit(lead, sales_person, planned, "Planned")

	_refresh_lead_summaries(reps)
	frappe.db.commit()
	print(
		f"Demo ready. Manager: {manager_email} / {PASSWORD}. Sales persons: "
		+ ", ".join(r[1] for r in reps)
		+ f" (password {PASSWORD})."
	)


def _refresh_lead_summaries(reps):
	status_for = {"Interested": "Interested", "Converted": "Opportunity", "Call Back": "Open", "Not Available": "Open", "Not Interested": "Do Not Contact"}
	for lead in frappe.get_all("Lead", filters={"lead_owner": ("in", [r[1] for r in reps])}, pluck="name"):
		visits = frappe.get_all(
			"Lead Visit",
			filters={"lead": lead, "status": "Completed"},
			fields=["name", "check_in_time", "check_out_time", "outcome", "notes", "sales_person", "distance_from_lead"],
			order_by="check_in_time asc",
		)
		if not visits:
			continue
		last = visits[-1]
		frappe.db.set_value(
			"Lead",
			lead,
			{
				"van_last_visit_on": last.check_in_time,
				"van_last_visit_outcome": last.outcome,
				"van_visit_count": len(visits),
				"status": status_for.get(last.outcome, "Open"),
			},
			update_modified=False,
		)
		owner = frappe.db.get_value("Lead", lead, "lead_owner")
		for idx, v in enumerate(visits, start=1):
			frappe.get_doc(
				{
					"doctype": "CRM Note",
					"parent": lead,
					"parenttype": "Lead",
					"parentfield": "notes",
					"idx": idx,
					"note": f"<p><b>{v.outcome}</b> ({v.sales_person}, {int(v.distance_from_lead or 0)} m from lead)</p><p>{v.notes}</p>",
					"added_by": owner,
					"added_on": v.check_out_time,
				}
			).db_insert()

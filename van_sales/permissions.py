"""Who sees which visits.

A sales person sees only their own visits. A Field Sales Manager (or an
ERPNext Sales Manager) sees the visits of every sales person under them in
the Sales Person tree, or all visits when they are not in the tree
themselves. System Managers see all.
"""

import frappe
from frappe.utils.nestedset import get_descendants_of

TEAM_ROLES = ("Field Sales Manager", "Sales Manager")
MANAGER_ROLES = (*TEAM_ROLES, "System Manager")


def get_sales_person(user: str | None = None) -> str | None:
	user = user or frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	if not employee:
		return None
	return frappe.db.get_value("Sales Person", {"employee": employee, "enabled": 1}, "name")


def is_manager(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool(set(MANAGER_ROLES) & set(frappe.get_roles(user)))


def visible_sales_persons(user: str | None = None) -> list[str] | None:
	"""Sales persons whose visits `user` may see; None means all of them."""
	user = user or frappe.session.user
	roles = frappe.get_roles(user)
	if user == "Administrator" or "System Manager" in roles:
		return None

	own = get_sales_person(user)
	if set(TEAM_ROLES) & set(roles):
		if not own:
			return None
		# The tree lookup only decides scope; the manager's own User Permission
		# on Employee would otherwise hide their team's Sales Person records.
		return [own, *get_descendants_of("Sales Person", own, ignore_permissions=True)]

	return [own] if own else []


def lead_visit_query(user=None):
	allowed = visible_sales_persons(user)
	if allowed is None:
		return ""
	if not allowed:
		return "1=0"
	return "`tabLead Visit`.`sales_person` in ({})".format(
		", ".join(frappe.db.escape(sp) for sp in allowed)
	)


def lead_visit_has_permission(doc, ptype=None, user=None):
	allowed = visible_sales_persons(user)
	if allowed is None or doc.is_new():
		return True
	return doc.sales_person in allowed

/**
 * Shared vocabulary for the lead visit screens.
 *
 * The statuses and outcomes are the Select options on Lead Visit, spelled
 * exactly as the desk spells them, so a filter on the desk and a badge on
 * the phone always mean the same thing.
 */

export const STATUS_THEME = {
	Planned: "blue",
	"Checked In": "orange",
	Completed: "green",
	Missed: "red",
	Cancelled: "gray",
}

export const OUTCOMES = ["Interested", "Call Back", "Not Available", "Not Interested", "Converted"]

export const OUTCOME_THEME = {
	Interested: "green",
	Converted: "green",
	"Call Back": "blue",
	"Not Available": "orange",
	"Not Interested": "red",
}

/** Directions in whatever maps app the phone hands geo links to. */
export function mapsUrl(latitude, longitude) {
	if (!latitude || !longitude) return ""
	return `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`
}

const pad = (n) => String(n).padStart(2, "0")

/** A Date as the value of an <input type="datetime-local">. */
export function toLocalInput(date) {
	return (
		`${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
		`T${pad(date.getHours())}:${pad(date.getMinutes())}`
	)
}

/** A datetime-local value in the shape Frappe's Datetime field accepts. */
export function fromLocalInput(value) {
	return value ? `${value.replace("T", " ")}:00` : null
}

/** Tomorrow at ten, the usual answer to "when do we come back?". */
export function tomorrowMorning() {
	const d = new Date()
	d.setDate(d.getDate() + 1)
	d.setHours(10, 0, 0, 0)
	return toLocalInput(d)
}

/** Minutes as "45 min" / "1 h 20 min". */
export function durationLabel(minutes) {
	const m = Math.round(Number(minutes) || 0)
	if (m < 60) return `${m} min`
	return `${Math.floor(m / 60)} h${m % 60 ? ` ${m % 60} min` : ""}`
}

/** The periods the manager screens offer, as TabButtons options. */
export const RANGES = [
	{ label: "Today", value: "today" },
	{ label: "7 days", value: "week" },
	{ label: "30 days", value: "month" },
]

/** from_date / to_date for a RANGES value, ending today. */
export function rangeDates(range) {
	const end = new Date()
	const start = new Date()
	start.setDate(end.getDate() - ({ today: 0, week: 6, month: 29 }[range] ?? 6))
	const iso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
	return { from_date: iso(start), to_date: iso(end) }
}

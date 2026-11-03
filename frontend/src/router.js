/**
 * Routes mirror the route names the server hands down in `bootstrap.tabs`,
 * so adding a persona on the desk changes the app's navigation with nothing
 * to configure on the phone.
 */

import { createRouter, createWebHistory } from "vue-router"

import PlannedScreen from "./pages/PlannedScreen.vue"
import { restore, session } from "./data/session"

const routes = [
	{
		path: "/login",
		name: "login",
		component: () => import("./pages/Login.vue"),
		meta: { public: true },
	},
	{
		path: "/",
		component: () => import("./components/AppShell.vue"),
		children: [
			// Van sales
			// No `redirect` here: vue-router applies a redirect before any guard
			// runs, which sent every persona to van_home. The guard below picks
			// the home the server named.
			{ path: "", name: "gate", component: { render: () => null } },
			{ path: "van_home", name: "van_home", component: () => import("./pages/VanHome.vue") },
			{ path: "invoice", name: "invoice", component: () => import("./pages/Invoice.vue") },
			{
				path: "customers",
				name: "customers",
				component: () => import("./pages/Customers.vue"),
			},
			{
				path: "replenish",
				name: "replenish",
				component: () => import("./pages/Replenish.vue"),
			},
			{ path: "profile", name: "profile", component: () => import("./pages/Profile.vue") },

			// Sale flow
			{ path: "items", name: "items", component: () => import("./pages/Items.vue") },
			{ path: "scan", name: "scan", component: () => import("./pages/Scan.vue") },
			{ path: "payment", name: "payment", component: () => import("./pages/Payment.vue") },
			{
				path: "receipt/:name",
				name: "receipt",
				component: () => import("./pages/Receipt.vue"),
			},
			{
				path: "customer/:id",
				name: "customer",
				component: () => import("./pages/Customer.vue"),
			},
			{
				path: "statement/:id",
				name: "statement",
				component: () => import("./pages/Statement.vue"),
			},
			{
				path: "invoice-view/:name",
				name: "invoice-view",
				component: () => import("./pages/InvoiceView.vue"),
			},
			{
				path: "credit-note/:invoice",
				name: "credit-note",
				component: () => import("./pages/CreditNote.vue"),
			},

			// Lead visits
			{ path: "visits", name: "visits", component: () => import("./pages/Visits.vue") },
			{ path: "leads", name: "leads", component: () => import("./pages/Leads.vue") },
			{
				path: "visit_history",
				name: "visit_history",
				component: () => import("./pages/VisitHistory.vue"),
			},
			{
				path: "visit/:name",
				name: "visit",
				component: () => import("./pages/Visit.vue"),
			},
			{
				path: "lead_activity",
				name: "lead_activity",
				component: () => import("./pages/LeadActivity.vue"),
			},
			{
				path: "team_visits",
				name: "team_visits",
				component: () => import("./pages/TeamVisits.vue"),
			},

			// Personas whose backends are not built yet. These render what the
			// screen will do rather than a fake one, so a demo never implies
			// working functionality that is not there.
			...[
				"collect",
				"presales_home",
				"order",
				"orders",
				"approvals",
				"team",
				"trip",
				"deliveries",
				"picking",
				"loading",
				"shortages",
				"requests",
				"dashboard",
				"sales",
				"alerts",
				"reports",
			].map((screen) => ({
				path: screen,
				name: screen,
				component: PlannedScreen,
				props: { screen },
			})),
		],
	},
	{ path: "/:pathMatch(.*)*", redirect: "/" },
]

const router = createRouter({
	history: createWebHistory("/van_sales"),
	routes,
})

router.beforeEach(async (to) => {
	if (!session.ready) await restore()

	if (to.meta.public) {
		return session.signedIn ? { name: "gate" } : true
	}

	if (!session.signedIn) return { name: "login" }

	// The server decides where a rep lands: a driver opens on the trip, a
	// picker on the pick list. Hardcoding "van_home" would strand every other
	// persona on a screen they have no tab for.
	if (to.name === "gate") {
		return { name: session.bootstrap?.home || "van_home" }
	}

	return true
})

export default router

<template>
	<!--
		Leads to visit.

		A rep sees the leads they own or are assigned to on the desk; a manager
		sees every open lead, because planning the team's visits is their job.
		Each lead carries its last visit, so "when were we last there and how
		did it go" is answered before the rep decides to go again.
	-->
	<div>
		<PageHeader
			title="Leads"
			:subtitle="manager ? 'All open leads' : 'Assigned to you'"
		/>

		<ScreenBody>
			<FormControl
				v-model="search"
				type="text"
				size="md"
				placeholder="Search name, company or city"
			/>

			<div v-if="list.loading.value && !list.data.value" class="py-6 text-center">
				<LoadingIndicator class="mx-auto h-5 w-5 text-ink-blue-2" />
			</div>

			<ErrorState
				v-else-if="list.error.value"
				:message="list.error.value"
				:offline="list.offline.value"
				:on-retry="list.reload"
			/>

			<EmptyState
				v-else-if="!list.data.value?.length"
				:text="
					search
						? 'No lead matches that search.'
						: 'No open leads are assigned to you. Leads are assigned on the desk.'
				"
			/>

			<template v-else>
				<p class="text-p-sm font-medium uppercase tracking-wide text-ink-gray-5">
					{{ list.data.value.length }} lead{{ list.data.value.length === 1 ? "" : "s" }}
				</p>

				<div
					v-for="lead in list.data.value"
					:key="lead.name"
					class="rounded-lg border border-outline-gray-2 bg-surface-white p-3.5 shadow-sm"
				>
					<div class="flex items-start gap-3">
						<div class="min-w-0 flex-1">
							<p class="truncate text-[14.5px] font-semibold text-ink-gray-8">
								{{ lead.lead_name }}
							</p>
							<p class="mt-0.5 truncate text-xs text-ink-gray-6">
								{{ [lead.company_name, lead.city].filter(Boolean).join(" · ") }}
							</p>
						</div>
						<Badge theme="gray" variant="subtle" size="sm">{{ lead.status }}</Badge>
					</div>

					<div class="mt-2.5 flex flex-col gap-1 text-xs text-ink-gray-6">
						<p v-if="lead.van_last_visit_on">
							Last visit {{ shortDate(lead.van_last_visit_on) }} ·
							<span :class="outcomeInk(lead.van_last_visit_outcome)">{{
								lead.van_last_visit_outcome
							}}</span>
							· {{ lead.van_visit_count }} visit{{
								lead.van_visit_count === 1 ? "" : "s"
							}}
						</p>
						<p v-else>Not visited yet</p>
						<p v-if="lead.next_visit" class="font-semibold text-ink-blue-2">
							Next visit {{ shortDate(lead.next_visit) }}
							{{ timeOfDay(lead.next_visit) }}
						</p>
						<p v-if="!lead.van_latitude" class="text-ink-amber-3">
							No map location yet. The first check-in pins it.
						</p>
					</div>

					<div class="mt-3 flex gap-2">
						<Button class="h-10 flex-1" @click="openPlan(lead)">Plan visit</Button>
						<CheckInButton
							v-if="!manager"
							:lead="lead.name"
							label="Visit now"
							button-class="h-10 flex-1"
						/>
						<Button
							v-if="lead.van_latitude"
							class="h-10"
							icon="navigation"
							aria-label="Navigate"
							@click="openMaps(lead)"
						/>
					</div>
				</div>
			</template>
		</ScreenBody>

		<Dialog v-model="planOpen" :options="{ title: planTitle }">
			<template #body-content>
				<div class="flex flex-col gap-3">
					<FormControl
						v-if="team.length > 1"
						v-model="plan.sales_person"
						type="select"
						size="md"
						label="Sales person"
						:options="team"
					/>
					<FormControl
						v-model="plan.planned_on"
						type="datetime-local"
						size="md"
						label="When"
					/>
					<FormControl
						v-model="plan.purpose"
						type="textarea"
						size="md"
						label="Purpose"
						placeholder="Product demo, price discussion, collect documents…"
					/>
					<ErrorMessage :message="planError" />
				</div>
			</template>
			<template #actions>
				<Button
					class="w-full"
					variant="solid"
					theme="blue"
					:loading="planning"
					@click="submitPlan"
				>
					Plan visit
				</Button>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import {
	Badge,
	Button,
	Dialog,
	ErrorMessage,
	FormControl,
	LoadingIndicator,
	toast,
} from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import CheckInButton from "../components/CheckInButton.vue"
import EmptyState from "../components/EmptyState.vue"
import ErrorState from "../components/ErrorState.vue"
import PageHeader from "../components/PageHeader.vue"
import ScreenBody from "../components/ScreenBody.vue"
import { api } from "../data/api"
import { shortDate, timeOfDay } from "../data/format"
import { session } from "../data/session"
import { useAsync } from "../data/useAsync"
import { OUTCOME_THEME, fromLocalInput, mapsUrl, tomorrowMorning } from "../data/visits"

const manager = computed(() => session.persona === "field_manager")

const search = ref("")
const query = ref("")
let debounce = null
watch(search, (value) => {
	clearTimeout(debounce)
	debounce = setTimeout(() => (query.value = value.trim()), 300)
})

const list = useAsync(() => api.myLeads(query.value || undefined), [query])

// Who a visit can be planned for. A rep only ever plans for themselves, so
// the picker only appears for someone with a team.
const teamData = useAsync(() => api.visitTeam())
const team = computed(() => teamData.data.value?.sales_persons ?? [])

const planOpen = ref(false)
const planning = ref(false)
const planError = ref("")
const planLead = ref(null)
const plan = reactive({ sales_person: "", planned_on: "", purpose: "" })

const planTitle = computed(() =>
	planLead.value ? `Plan visit to ${planLead.value.lead_name}` : "Plan visit",
)

function openPlan(lead) {
	planLead.value = lead
	plan.sales_person = teamData.data.value?.mine || team.value[0] || ""
	plan.planned_on = tomorrowMorning()
	plan.purpose = ""
	planError.value = ""
	planOpen.value = true
}

async function submitPlan() {
	if (!plan.planned_on) {
		planError.value = "Choose when the visit is."
		return
	}
	planning.value = true
	planError.value = ""
	try {
		await api.planVisit({
			lead: planLead.value.name,
			planned_on: fromLocalInput(plan.planned_on),
			purpose: plan.purpose || undefined,
			sales_person: plan.sales_person || undefined,
		})
		planOpen.value = false
		toast.success("Visit planned")
		list.reload()
	} catch (error) {
		planError.value = error.message
	} finally {
		planning.value = false
	}
}

function outcomeInk(outcome) {
	return (
		{ green: "text-ink-green-3", red: "text-ink-red-4", blue: "text-ink-blue-2" }[
			OUTCOME_THEME[outcome]
		] ?? "text-ink-gray-7"
	)
}

function openMaps(lead) {
	window.open(mapsUrl(lead.van_latitude, lead.van_longitude), "_blank")
}
</script>

<template>
	<!--
		One lead visit: check in, record what happened, check out.

		Check-out asks for the outcome and the notes in one place, and only
		then for the next visit, because "when do we come back" is decided by
		how this one went. An out-of-range check-in is accepted, never blocked
		-- the lead may have moved, the pin may be wrong -- but the rep says
		why, and the manager sees both the distance and the reason.
	-->
	<div>
		<PageHeader :title="v?.lead_name ?? 'Visit'" :subtitle="route.params.name" back />

		<ScreenBody>
			<div v-if="visit.loading.value && !v" class="py-6 text-center">
				<LoadingIndicator class="mx-auto h-5 w-5 text-ink-blue-2" />
			</div>

			<ErrorState
				v-else-if="visit.error.value"
				:message="visit.error.value"
				:offline="visit.offline.value"
				:on-retry="visit.reload"
			/>

			<template v-else-if="v">
				<MoneyPanel>
					<div class="flex items-start gap-3">
						<div class="min-w-0 flex-1">
							<p class="text-[11px] font-bold uppercase tracking-[0.1em] text-ink-gray-5">
								{{ v.visit_type }} visit · {{ v.sales_person }}
							</p>
							<p class="mt-1 text-[20px] font-semibold -tracking-[0.02em] text-ink-gray-9">
								{{ v.lead_name }}
							</p>
							<p class="mt-0.5 text-xs text-ink-gray-6">
								{{ [v.company_name, v.city].filter(Boolean).join(" · ") }}
							</p>
						</div>
						<Badge :theme="STATUS_THEME[v.status] ?? 'gray'" variant="subtle" size="lg">
							{{ v.status }}
						</Badge>
					</div>

					<div class="mt-3 grid grid-cols-2 gap-2.5">
						<div class="rounded-md bg-surface-gray-2 p-2.5">
							<p class="text-p-sm text-ink-gray-5">Planned</p>
							<p class="mt-0.5 text-sm font-semibold text-ink-gray-8">
								{{ v.planned_on ? `${shortDate(v.planned_on)} ${timeOfDay(v.planned_on)}` : "Unplanned" }}
							</p>
						</div>
						<div class="rounded-md bg-surface-gray-2 p-2.5">
							<p class="text-p-sm text-ink-gray-5">Checked in</p>
							<p class="mt-0.5 text-sm font-semibold text-ink-gray-8">
								{{ v.check_in_time ? timeOfDay(v.check_in_time) : "Not yet" }}
								<span v-if="v.duration_minutes" class="font-normal text-ink-gray-5">
									· {{ durationLabel(v.duration_minutes) }}
								</span>
							</p>
						</div>
					</div>

					<p v-if="v.purpose" class="mt-3 text-[13px] leading-5 text-ink-gray-7">
						{{ v.purpose }}
					</p>

					<div class="mt-3 flex gap-2">
						<Button
							v-if="v.lead_latitude"
							class="h-10 flex-1"
							icon-left="navigation"
							@click="openMaps"
						>
							Navigate
						</Button>
						<Button v-if="v.mobile_no" class="h-10 flex-1" icon-left="phone" @click="call">
							Call
						</Button>
					</div>
				</MoneyPanel>

				<Alert
					v-if="v.out_of_range"
					theme="red"
					title="Out of range"
					:dismissable="false"
					:description="`Checked in ${distanceLabel(v.distance_from_lead)} from the lead's location${gpsNote}. The allowed radius is ${policy.visit_allowed_radius ?? 200} m.`"
				/>
				<Alert
					v-else-if="v.check_in_time && !v.lead_latitude"
					theme="yellow"
					title="Lead location not saved"
					:dismissable="false"
					:description="`The GPS fix was too rough to pin this lead${gpsNote}. The next visit with a clear GPS signal will pin it.`"
				/>
				<Alert
					v-else-if="v.check_in_time && v.distance_from_lead !== null"
					theme="green"
					title="At the lead's location"
					:dismissable="false"
					:description="`Checked in ${distanceLabel(v.distance_from_lead)} from the lead${v.location_source === 'Simulated (Demo)' ? ' (simulated location)' : gpsNote}.`"
				/>

				<!-- Planned: go there and check in -->
				<template v-if="canAct && ['Planned', 'Missed'].includes(v.status)">
					<CheckInButton :visit="v.name" size="lg" button-class="h-touch w-full" @done="visit.reload" />
					<Button
						v-if="v.status === 'Planned'"
						class="h-touch w-full !text-ink-red-3"
						variant="outline"
						@click="cancelOpen = true"
					>
						Cancel visit
					</Button>
				</template>

				<!-- Checked in: what happened -->
				<div
					v-if="canAct && v.status === 'Checked In'"
					class="flex flex-col gap-3 rounded-lg border border-outline-gray-2 bg-surface-white p-3.5 shadow-sm"
				>
					<p class="text-p-sm font-medium uppercase tracking-wide text-ink-gray-5">Outcome</p>
					<div class="flex flex-wrap gap-2">
						<button
							v-for="option in OUTCOMES"
							:key="option"
							type="button"
							class="min-h-10 rounded-full border px-3.5 text-[13px] font-semibold"
							:class="
								form.outcome === option
									? 'border-outline-gray-5 bg-surface-gray-7 text-ink-white'
									: 'border-outline-gray-2 bg-surface-white text-ink-gray-7'
							"
							@click="form.outcome = option"
						>
							{{ option }}
						</button>
					</div>

					<FormControl
						v-model="form.notes"
						type="textarea"
						size="md"
						:label="policy.visit_notes_mandatory ? 'Notes (required)' : 'Notes'"
						placeholder="Who you met, what was discussed, what they need next"
						:rows="5"
					/>

					<FormControl
						v-if="v.out_of_range"
						v-model="form.out_of_range_reason"
						type="textarea"
						size="md"
						label="Why were you away from the lead's location?"
						placeholder="Met at their other office, pin is wrong, met at a site…"
						:rows="2"
					/>

					<label class="flex items-center gap-2.5 text-sm text-ink-gray-8">
						<input v-model="followUp" type="checkbox" class="h-5 w-5 rounded" />
						Plan a follow-up visit
					</label>
					<FormControl
						v-if="followUp"
						v-model="form.next_visit_on"
						type="datetime-local"
						size="md"
						label="Next visit"
					/>

					<ErrorMessage :message="formError" />

					<Button
						class="h-touch w-full"
						variant="solid"
						theme="blue"
						:loading="saving"
						@click="checkOut"
					>
						Check out
					</Button>
				</div>

				<!-- Done: what was recorded -->
				<div
					v-if="['Completed', 'Missed', 'Cancelled'].includes(v.status) && (v.outcome || v.notes)"
					class="rounded-lg border border-outline-gray-2 bg-surface-white p-3.5 shadow-sm"
				>
					<div class="flex items-center justify-between">
						<p class="text-p-sm font-medium uppercase tracking-wide text-ink-gray-5">Notes</p>
						<Badge v-if="v.outcome" :theme="OUTCOME_THEME[v.outcome] ?? 'gray'" variant="subtle">
							{{ v.outcome }}
						</Badge>
					</div>
					<p class="mt-2 whitespace-pre-line text-[14px] leading-[21px] text-ink-gray-8">
						{{ v.notes || "No notes." }}
					</p>
					<p v-if="v.out_of_range_reason" class="mt-3 text-xs text-ink-red-4">
						Out-of-range reason: {{ v.out_of_range_reason }}
					</p>
					<p v-if="v.auto_closed" class="mt-3 text-xs text-ink-amber-3">
						Nobody checked out, so this visit was closed at the end of its day.
					</p>
				</div>

				<Button
					v-if="v.followup_visit"
					class="h-touch w-full"
					icon-right="chevron-right"
					@click="router.push({ name: 'visit', params: { name: v.followup_visit } })"
				>
					Follow-up visit {{ v.next_visit_on ? shortDate(v.next_visit_on) : "" }}
				</Button>
			</template>
		</ScreenBody>

		<Dialog
			v-model="cancelOpen"
			:options="{
				title: 'Cancel this visit?',
				message: 'It stays on record as Cancelled and stops counting as planned.',
				actions: [
					{ label: 'Cancel visit', variant: 'solid', theme: 'red', onClick: cancelVisit },
					{ label: 'Keep it', onClick: () => (cancelOpen = false) },
				],
			}"
		/>
	</div>
</template>

<script setup>
import {
	Alert,
	Badge,
	Button,
	Dialog,
	ErrorMessage,
	FormControl,
	LoadingIndicator,
	toast,
} from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import CheckInButton from "../components/CheckInButton.vue"
import ErrorState from "../components/ErrorState.vue"
import MoneyPanel from "../components/MoneyPanel.vue"
import PageHeader from "../components/PageHeader.vue"
import ScreenBody from "../components/ScreenBody.vue"
import { api } from "../data/api"
import { shortDate, timeOfDay } from "../data/format"
import { accuracyLabel, captureGeo, distanceLabel } from "../data/geo"
import { policy } from "../data/session"
import { useAsync } from "../data/useAsync"
import {
	OUTCOMES,
	OUTCOME_THEME,
	STATUS_THEME,
	durationLabel,
	fromLocalInput,
	mapsUrl,
	tomorrowMorning,
} from "../data/visits"

const route = useRoute()
const router = useRouter()

const visit = useAsync(() => api.getVisit(route.params.name), [() => route.params.name])
const v = computed(() => visit.data.value)

// A manager can open any visit on their team, but only the rep it belongs
// to checks in and out of it.
const canAct = computed(() => Boolean(v.value?.is_mine))

// How far the check-in fix could be off, so a surprising distance can be
// read as weak GPS rather than the rep being elsewhere.
const gpsNote = computed(() =>
	v.value?.check_in_accuracy ? ` (GPS accuracy ${accuracyLabel(v.value.check_in_accuracy)})` : "",
)

const form = reactive({ outcome: "", notes: "", out_of_range_reason: "", next_visit_on: "" })
const followUp = ref(false)
const formError = ref("")
const saving = ref(false)
const cancelOpen = ref(false)

// An error is about the form as it was; once the rep changes it, it is stale.
watch([form, followUp], () => (formError.value = ""), { deep: true })

watch(followUp, (on) => {
	if (on && !form.next_visit_on) form.next_visit_on = tomorrowMorning()
})

async function checkOut() {
	formError.value = ""
	if (!form.outcome) return (formError.value = "Choose the outcome of the visit.")
	if (policy.value.visit_notes_mandatory && !form.notes.trim()) {
		return (formError.value = "Add notes about the visit.")
	}
	if (v.value.out_of_range && !form.out_of_range_reason.trim()) {
		return (formError.value = "Say why you checked in away from the lead's location.")
	}

	saving.value = true
	try {
		// Where the rep checked out is a nice-to-have, so it never waits on GPS.
		const geo = await captureGeo(true)
		const result = await api.checkOut({
			visit: v.value.name,
			outcome: form.outcome,
			notes: form.notes,
			out_of_range_reason: form.out_of_range_reason || undefined,
			next_visit_on: followUp.value ? fromLocalInput(form.next_visit_on) : undefined,
			latitude: geo?.latitude,
			longitude: geo?.longitude,
		})
		toast.success(
			result.followup_visit ? "Checked out. Follow-up visit planned." : "Checked out",
		)
		router.replace({ name: "visits" })
	} catch (error) {
		formError.value = error.message
	} finally {
		saving.value = false
	}
}

async function cancelVisit() {
	try {
		await api.cancelVisit(v.value.name)
		cancelOpen.value = false
		toast.success("Visit cancelled")
		visit.reload()
	} catch (error) {
		toast.error(error.message)
	}
}

function openMaps() {
	window.open(mapsUrl(v.value.lead_latitude, v.value.lead_longitude), "_blank")
}

function call() {
	window.location.href = `tel:${v.value.mobile_no}`
}
</script>

<template>
	<!--
		The field sales rep's day.

		The visit in progress leads, because a rep who is still checked in at
		the last stop cannot start the next one -- the server refuses a second
		open visit -- and the fix should be one tap away, not a puzzle.
	-->
	<div>
		<PageHeader title="My visits" :subtitle="subtitle">
			<template #right>
				<button
					type="button"
					class="flex h-9 w-9 items-center justify-center rounded-full active:bg-surface-gray-2"
					aria-label="Refresh"
					@click="reloadAll"
				>
					<FeatherIcon
						name="refresh-cw"
						class="h-[18px] w-[18px] text-ink-gray-6"
						:class="{ 'animate-spin': day.loading.value }"
					/>
				</button>
			</template>
		</PageHeader>

		<ScreenBody>
			<div v-if="day.loading.value && !d" class="py-6 text-center">
				<LoadingIndicator class="mx-auto h-5 w-5 text-ink-blue-2" />
			</div>

			<ErrorState
				v-else-if="day.error.value"
				:message="day.error.value"
				:offline="day.offline.value"
				:on-retry="day.reload"
			/>

			<template v-else-if="d">
				<MoneyPanel v-if="d.active_visit">
					<p class="text-[11px] font-bold uppercase tracking-[0.1em] text-ink-amber-3">
						Checked in · {{ timeOfDay(d.active_visit.check_in_time) }}
					</p>
					<p class="mt-1 text-[20px] font-semibold -tracking-[0.02em] text-ink-gray-9">
						{{ d.active_visit.lead_name }}
					</p>
					<p class="mt-0.5 text-xs text-ink-gray-6">
						{{
							[d.active_visit.company_name, d.active_visit.city]
								.filter(Boolean)
								.join(" · ")
						}}
					</p>
					<p v-if="d.active_visit.out_of_range" class="mt-2 text-xs text-ink-red-4">
						{{ distanceLabel(d.active_visit.distance_from_lead) }} from the lead's
						location. You will be asked why at check-out.
					</p>
					<Button
						class="mt-3 h-touch w-full"
						variant="solid"
						theme="blue"
						@click="openVisit(d.active_visit.name)"
					>
						Add notes &amp; check out
					</Button>
				</MoneyPanel>

				<div class="flex gap-2.5">
					<StatTile label="Planned" :value="String(d.stats.planned)" />
					<StatTile label="Done" :value="String(d.stats.completed)" tone="green" />
					<StatTile label="Pending" :value="String(d.stats.pending)" />
					<StatTile
						label="Out of range"
						:value="String(d.stats.out_of_range)"
						:tone="d.stats.out_of_range ? 'red' : 'gray'"
					/>
				</div>

				<div class="flex items-center justify-between">
					<span class="text-p-sm font-medium uppercase tracking-wide text-ink-gray-5">
						Today · {{ shortDate(d.today) }}
					</span>
					<button
						type="button"
						class="text-[12.5px] font-semibold text-ink-blue-2"
						@click="router.push({ name: 'leads' })"
					>
						Unplanned visit
					</button>
				</div>

				<EmptyState
					v-if="!d.visits.length"
					text="No visits planned for today. Plan one from a lead, or start an unplanned visit."
				/>

				<VisitCard v-for="visit in d.visits" :key="visit.name" :visit="visit" :here="here">
					<template v-if="['Planned', 'Missed'].includes(visit.status)" #actions>
						<CheckInButton
							v-if="!d.active_visit"
							:visit="visit.name"
							button-class="h-10 flex-1"
						/>
						<Button
							v-if="visit.lead_latitude"
							class="h-10"
							icon-left="navigation"
							@click="openMaps(visit)"
						>
							Navigate
						</Button>
						<Button
							v-if="visit.mobile_no"
							class="h-10"
							icon="phone"
							aria-label="Call"
							@click="call(visit.mobile_no)"
						/>
					</template>
				</VisitCard>
			</template>
		</ScreenBody>
	</div>
</template>

<script setup>
import { Button, FeatherIcon, LoadingIndicator } from "frappe-ui"
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import CheckInButton from "../components/CheckInButton.vue"
import EmptyState from "../components/EmptyState.vue"
import ErrorState from "../components/ErrorState.vue"
import MoneyPanel from "../components/MoneyPanel.vue"
import PageHeader from "../components/PageHeader.vue"
import ScreenBody from "../components/ScreenBody.vue"
import StatTile from "../components/StatTile.vue"
import VisitCard from "../components/VisitCard.vue"
import { api } from "../data/api"
import { shortDate, timeOfDay } from "../data/format"
import { distanceLabel, lastKnownPosition, requestLocationAccess } from "../data/geo"
import { refresh, session } from "../data/session"
import { useAsync } from "../data/useAsync"
import { mapsUrl } from "../data/visits"

const router = useRouter()

const day = useAsync(() => api.myDay())
const d = computed(() => day.data.value)

const here = ref(lastKnownPosition())

const subtitle = computed(() => {
	const name = session.bootstrap?.user?.full_name ?? ""
	return d.value?.sales_person && d.value.sales_person !== name
		? `${name} · ${d.value.sales_person}`
		: name
})

function openVisit(name) {
	router.push({ name: "visit", params: { name } })
}

function openMaps(visit) {
	window.open(mapsUrl(visit.lead_latitude, visit.lead_longitude), "_blank")
}

function call(number) {
	window.location.href = `tel:${number}`
}

async function reloadAll() {
	await Promise.allSettled([day.reload(), refresh()])
}

// Warm a position on opening the day, so "1.2 km away" is there without the
// rep asking and the first check-in does not start from a cold GPS.
onMounted(async () => {
	if (await requestLocationAccess()) here.value = lastKnownPosition()
})
</script>

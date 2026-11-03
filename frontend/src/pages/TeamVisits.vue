<template>
	<!--
		What the team wrote at their visits, newest first.

		Out-of-range check-ins show the distance and the rep's reason side by
		side, so the manager judges the reason rather than just the flag.
	-->
	<div>
		<PageHeader title="Visit notes" :subtitle="salesPerson || 'Whole team'" />

		<ScreenBody>
			<TabButtons v-model="range" class="w-full" :buttons="RANGES" />

			<FormControl
				v-model="salesPerson"
				type="select"
				size="md"
				:options="[
					{ label: 'Whole team', value: '' },
					...(d?.sales_persons ?? []).map((sp) => ({ label: sp, value: sp })),
				]"
			/>

			<div v-if="activity.loading.value && !d" class="py-6 text-center">
				<LoadingIndicator class="mx-auto h-5 w-5 text-ink-blue-2" />
			</div>

			<ErrorState
				v-else-if="activity.error.value"
				:message="activity.error.value"
				:offline="activity.offline.value"
				:on-retry="activity.reload"
			/>

			<EmptyState v-else-if="!visits.length" text="No completed visits in this period." />

			<template v-else>
				<template v-for="visit in visits" :key="visit.name">
					<VisitCard :visit="visit" show-sales-person with-date />
					<p
						v-if="visit.out_of_range && visit.out_of_range_reason"
						class="-mt-2 px-1 text-xs text-ink-red-4"
					>
						Reason: {{ visit.out_of_range_reason }}
					</p>
				</template>
			</template>
		</ScreenBody>
	</div>
</template>

<script setup>
import { FormControl, LoadingIndicator, TabButtons } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "../components/EmptyState.vue"
import ErrorState from "../components/ErrorState.vue"
import PageHeader from "../components/PageHeader.vue"
import ScreenBody from "../components/ScreenBody.vue"
import VisitCard from "../components/VisitCard.vue"
import { api } from "../data/api"
import { useAsync } from "../data/useAsync"
import { RANGES, rangeDates } from "../data/visits"

const route = useRoute()

const range = ref("week")
const salesPerson = ref("")

// The activity screen links here with a person and period already chosen.
watch(
	() => route.query,
	(query) => {
		if (RANGES.some((r) => r.value === query.range)) range.value = query.range
		salesPerson.value = query.sales_person ?? ""
	},
	{ immediate: true },
)

const activity = useAsync(
	() =>
		api.leadActivity({
			...rangeDates(range.value),
			sales_person: salesPerson.value || undefined,
		}),
	[range, salesPerson],
)
const d = computed(() => activity.data.value)

const visits = computed(() =>
	(d.value?.recent ?? []).map((row) => ({
		...row,
		status: "Completed",
		distance_from_lead: row.distance,
	})),
)
</script>

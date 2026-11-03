<template>
	<!--
		Sales person wise lead activity, for the manager.

		The same figures as the Lead Activity Dashboard on the desk and the
		Sales Person Lead Activity report -- all three read
		van_sales.api.lead_activity -- so a number quoted from the phone in a
		review matches the one on the screen in the office.
	-->
	<div>
		<PageHeader title="Lead activity" :subtitle="rangeLabel">
			<template #right>
				<button
					type="button"
					class="flex h-9 w-9 items-center justify-center rounded-full active:bg-surface-gray-2"
					aria-label="Refresh"
					@click="activity.reload"
				>
					<FeatherIcon
						name="refresh-cw"
						class="h-[18px] w-[18px] text-ink-gray-6"
						:class="{ 'animate-spin': activity.loading.value }"
					/>
				</button>
			</template>
		</PageHeader>

		<ScreenBody>
			<TabButtons v-model="range" class="w-full" :buttons="RANGES" />

			<div v-if="activity.loading.value && !d" class="py-6 text-center">
				<LoadingIndicator class="mx-auto h-5 w-5 text-ink-blue-2" />
			</div>

			<ErrorState
				v-else-if="activity.error.value"
				:message="activity.error.value"
				:offline="activity.offline.value"
				:on-retry="activity.reload"
			/>

			<template v-else-if="d">
				<div class="grid grid-cols-3 gap-2.5">
					<StatTile label="Planned" :value="String(d.cards.planned)" />
					<StatTile label="Completed" :value="String(d.cards.completed)" tone="green" />
					<StatTile
						label="Missed"
						:value="String(d.cards.missed)"
						:tone="d.cards.missed ? 'red' : 'gray'"
					/>
					<StatTile
						label="Out of range"
						:value="String(d.cards.out_of_range)"
						:tone="d.cards.out_of_range ? 'red' : 'gray'"
					/>
					<StatTile label="Converted" :value="String(d.cards.converted)" tone="green" />
					<StatTile label="Open leads" :value="String(d.cards.leads_assigned)" />
				</div>

				<p class="text-p-sm font-medium uppercase tracking-wide text-ink-gray-5">
					By sales person
				</p>

				<EmptyState v-if="!d.people.length" text="No visits in this period." />

				<button
					v-for="person in d.people"
					:key="person.sales_person"
					type="button"
					class="rounded-lg border border-outline-gray-2 bg-surface-white p-3.5 text-left shadow-sm active:bg-surface-gray-1"
					@click="
						router.push({
							name: 'team_visits',
							query: { sales_person: person.sales_person, range },
						})
					"
				>
					<div class="flex items-start gap-3">
						<div class="min-w-0 flex-1">
							<p class="truncate text-[15px] font-semibold text-ink-gray-8">
								{{ person.sales_person }}
							</p>
							<p class="mt-0.5 text-xs text-ink-gray-5">
								{{ person.leads_visited }} lead{{ person.leads_visited === 1 ? "" : "s" }}
								visited · {{ person.leads_assigned }} open
								<template v-if="person.last_activity">
									· last {{ shortDate(person.last_activity) }}
									{{ timeOfDay(person.last_activity) }}
								</template>
							</p>
						</div>
						<div class="shrink-0 text-right">
							<p class="money text-lg font-semibold" :class="completionInk(person.completion)">
								{{ Math.round(person.completion) }}%
							</p>
							<p class="text-[10.5px] text-ink-gray-5">
								{{ person.completed }}/{{ person.total_visits }} done
							</p>
						</div>
					</div>

					<!-- Completed, still open and missed, out of every visit in the period -->
					<div class="mt-3 flex h-1.5 overflow-hidden rounded-sm bg-surface-gray-2">
						<div :style="{ flex: person.completed, backgroundColor: '#17B26A' }" />
						<div :style="{ flex: person.pending, backgroundColor: '#84CAFF' }" />
						<div :style="{ flex: person.missed, backgroundColor: '#F97066' }" />
					</div>

					<div class="mt-2.5 flex flex-wrap gap-1.5">
						<Badge v-if="person.missed" theme="red" variant="subtle" size="sm">
							{{ person.missed }} missed
						</Badge>
						<Badge v-if="person.out_of_range" theme="red" variant="outline" size="sm">
							{{ person.out_of_range }} out of range
						</Badge>
						<Badge v-if="person.interested" theme="green" variant="subtle" size="sm">
							{{ person.interested }} interested
						</Badge>
						<Badge v-if="person.converted" theme="green" variant="outline" size="sm">
							{{ person.converted }} converted
						</Badge>
						<Badge v-if="person.unplanned" theme="gray" variant="subtle" size="sm">
							{{ person.unplanned }} unplanned
						</Badge>
						<Badge v-if="person.avg_duration" theme="gray" variant="outline" size="sm">
							avg {{ durationLabel(person.avg_duration) }}
						</Badge>
					</div>
				</button>

				<template v-if="d.outcomes.length">
					<p class="text-p-sm font-medium uppercase tracking-wide text-ink-gray-5">
						Outcomes
					</p>
					<div class="rounded-lg border border-outline-gray-2 bg-surface-white p-3.5 shadow-sm">
						<div
							v-for="row in d.outcomes"
							:key="row.outcome"
							class="flex items-center gap-3 py-1.5"
						>
							<span class="w-28 shrink-0 text-[13px] text-ink-gray-7">{{ row.outcome }}</span>
							<div class="h-2 flex-1 overflow-hidden rounded-sm bg-surface-gray-2">
								<div
									class="h-full"
									:style="{
										width: `${(100 * row.count) / outcomeMax}%`,
										backgroundColor: OUTCOME_COLOR[row.outcome] ?? '#98A2B3',
									}"
								/>
							</div>
							<span class="money w-8 text-right text-[13px] font-semibold text-ink-gray-8">
								{{ row.count }}
							</span>
						</div>
					</div>
				</template>
			</template>
		</ScreenBody>
	</div>
</template>

<script setup>
import { Badge, FeatherIcon, LoadingIndicator, TabButtons } from "frappe-ui"
import { computed, ref } from "vue"
import { useRouter } from "vue-router"

import EmptyState from "../components/EmptyState.vue"
import ErrorState from "../components/ErrorState.vue"
import PageHeader from "../components/PageHeader.vue"
import ScreenBody from "../components/ScreenBody.vue"
import StatTile from "../components/StatTile.vue"
import { api } from "../data/api"
import { shortDate, timeOfDay } from "../data/format"
import { useAsync } from "../data/useAsync"
import { RANGES, durationLabel, rangeDates } from "../data/visits"

const router = useRouter()

const OUTCOME_COLOR = {
	Interested: "#17B26A",
	Converted: "#079455",
	"Call Back": "#2E90FA",
	"Not Available": "#FDB022",
	"Not Interested": "#F97066",
}

const range = ref("week")
const activity = useAsync(() => api.leadActivity(rangeDates(range.value)), [range])
const d = computed(() => activity.data.value)

const rangeLabel = computed(() =>
	d.value ? `${shortDate(d.value.from_date)} – ${shortDate(d.value.to_date)}` : "",
)

const outcomeMax = computed(() =>
	Math.max(1, ...(d.value?.outcomes ?? []).map((row) => row.count)),
)

function completionInk(pct) {
	if (pct >= 75) return "text-ink-green-3"
	if (pct >= 50) return "text-ink-amber-3"
	return "text-ink-red-4"
}
</script>

<template>
	<!-- One lead visit in a list. The actions slot is where the screen puts
	     what can be done next; the card itself only opens the visit. -->
	<div
		role="button"
		tabindex="0"
		class="rounded-lg border border-outline-gray-2 bg-surface-white p-3.5 shadow-sm active:bg-surface-gray-1"
		@click="open"
		@keydown.enter="open"
	>
		<div class="flex items-start gap-3">
			<div class="w-12 shrink-0 pt-0.5">
				<p class="money text-[15px] font-semibold text-ink-gray-8">{{ time }}</p>
				<p class="text-[11px] text-ink-gray-5">{{ day }}</p>
			</div>

			<div class="min-w-0 flex-1">
				<p class="truncate text-[14.5px] font-semibold text-ink-gray-8">
					{{ visit.lead_name }}
				</p>
				<p class="mt-0.5 truncate text-xs text-ink-gray-6">
					{{ [visit.company_name, visit.city].filter(Boolean).join(" · ") || visit.lead }}
				</p>
				<p v-if="showSalesPerson" class="mt-0.5 truncate text-xs text-ink-gray-5">
					{{ visit.sales_person }}
				</p>
			</div>

			<div class="flex shrink-0 flex-col items-end gap-1">
				<Badge :theme="STATUS_THEME[visit.status] ?? 'gray'" variant="subtle" size="sm">
					{{ visit.status }}
				</Badge>
				<span v-if="away" class="text-[11px] text-ink-gray-5">{{ away }} away</span>
			</div>
		</div>

		<div v-if="visit.outcome || visit.out_of_range" class="mt-2.5 flex flex-wrap gap-1.5">
			<Badge
				v-if="visit.outcome"
				:theme="OUTCOME_THEME[visit.outcome] ?? 'gray'"
				variant="outline"
				size="sm"
			>
				{{ visit.outcome }}
			</Badge>
			<Badge v-if="visit.out_of_range" theme="red" variant="outline" size="sm">
				Out of range · {{ distanceLabel(visit.distance_from_lead) }}
			</Badge>
			<Badge v-if="visit.location_source === 'Simulated (Demo)'" theme="gray" size="sm">
				Simulated
			</Badge>
		</div>

		<p v-if="visit.purpose && !visit.notes" class="mt-2 line-clamp-2 text-xs text-ink-gray-6">
			{{ visit.purpose }}
		</p>
		<p
			v-if="visit.notes"
			class="mt-2 line-clamp-3 whitespace-pre-line text-[13px] leading-5 text-ink-gray-7"
		>
			{{ visit.notes }}
		</p>

		<div v-if="$slots.actions" class="mt-3 flex gap-2" @click.stop>
			<slot name="actions" />
		</div>
	</div>
</template>

<script setup>
import { Badge } from "frappe-ui"
import { computed } from "vue"
import { useRouter } from "vue-router"

import { shortDate, timeOfDay } from "../data/format"
import { distanceLabel, metresBetween } from "../data/geo"
import { OUTCOME_THEME, STATUS_THEME } from "../data/visits"

const props = defineProps({
	visit: { type: Object, required: true },
	/** Where the rep is now, to show how far the lead is. */
	here: { type: Object, default: null },
	showSalesPerson: { type: Boolean, default: false },
	/** Show the date under the time, for lists spanning several days. */
	withDate: { type: Boolean, default: false },
})

const router = useRouter()

const when = computed(() => props.visit.check_in_time || props.visit.planned_on)
const time = computed(() => timeOfDay(when.value) || "—")
const day = computed(() => (props.withDate ? shortDate(when.value) : props.visit.visit_type))

const away = computed(() => {
	if (!props.here || !props.visit.lead_latitude) return ""
	if (!["Planned", "Missed"].includes(props.visit.status)) return ""
	return distanceLabel(
		metresBetween(props.here, {
			latitude: props.visit.lead_latitude,
			longitude: props.visit.lead_longitude,
		}),
	)
})

function open() {
	router.push({ name: "visit", params: { name: props.visit.name } })
}
</script>

<template>
	<!--
		Check in to a planned visit, or start an unplanned one at a lead.

		The position is read live and at high accuracy, because the server
		measures it against the lead's pin: a stale fix would flag the rep as
		out of range for a stop they are standing at. When the phone cannot
		give one and the site allows it for a demo, the rep is offered a point
		near the lead instead, and the visit says so.
	-->
	<Button
		:size="size"
		:class="buttonClass"
		variant="solid"
		theme="blue"
		:loading="busy"
		@click.stop="start"
	>
		{{ locating ? "Finding GPS…" : label }}
	</Button>

	<Dialog
		v-model="simulateOpen"
		:options="{
			title: 'No location from this phone',
			message: `${simulateReason}\n\nFor this demo you can check in at a point near the lead instead. The visit will be marked Simulated.`,
			actions: [
				{
					label: 'Use demo location',
					variant: 'solid',
					theme: 'blue',
					loading: busy,
					onClick: () => post(null, true),
				},
				{ label: 'Cancel', onClick: () => (simulateOpen = false) },
			],
		}"
	/>
</template>

<script setup>
import { Button, Dialog, toast } from "frappe-ui"
import { ref } from "vue"
import { useRouter } from "vue-router"

import { api } from "../data/api"
import { currentPosition, distanceLabel } from "../data/geo"
import { policy } from "../data/session"

const props = defineProps({
	/** A planned visit to check in to. */
	visit: { type: String, default: null },
	/** Or a lead to start an unplanned visit at. */
	lead: { type: String, default: null },
	label: { type: String, default: "Check in" },
	size: { type: String, default: "md" },
	buttonClass: { type: String, default: "" },
})

const emit = defineEmits(["done"])

const router = useRouter()
const busy = ref(false)
const locating = ref(false)
const simulateOpen = ref(false)
const simulateReason = ref("")

async function start() {
	busy.value = true
	locating.value = true
	let position
	try {
		position = await currentPosition()
	} catch (error) {
		busy.value = false
		locating.value = false
		if (policy.value.allow_simulated_location) {
			simulateReason.value = error.message
			simulateOpen.value = true
		} else {
			toast.error(error.message)
		}
		return
	}
	locating.value = false
	await post(position, false)
}

async function post(position, simulated) {
	busy.value = true
	try {
		const visit = await api.checkIn({
			visit: props.visit ?? undefined,
			lead: props.visit ? undefined : props.lead,
			latitude: position?.latitude,
			longitude: position?.longitude,
			accuracy: position?.accuracy,
			simulated: simulated ? 1 : 0,
		})
		simulateOpen.value = false

		// The visit screen this lands on repeats an out-of-range check-in as an
		// alert, so the toast only has to name it.
		toast.success(
			visit.out_of_range
				? `Checked in ${distanceLabel(visit.distance_from_lead)} from the lead`
				: `Checked in at ${visit.lead_name}`,
		)

		emit("done", visit)
		router.push({ name: "visit", params: { name: visit.name } })
	} catch (error) {
		toast.error(error.message)
	} finally {
		busy.value = false
	}
}
</script>

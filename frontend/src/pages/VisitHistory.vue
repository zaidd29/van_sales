<template>
	<!-- The rep's own finished and missed visits, newest first. -->
	<div>
		<PageHeader title="Visit history" subtitle="Completed and missed visits" />

		<ScreenBody>
			<div v-if="history.loading.value && !history.data.value" class="py-6 text-center">
				<LoadingIndicator class="mx-auto h-5 w-5 text-ink-blue-2" />
			</div>

			<ErrorState
				v-else-if="history.error.value"
				:message="history.error.value"
				:offline="history.offline.value"
				:on-retry="history.reload"
			/>

			<EmptyState v-else-if="!history.data.value?.length" text="No visits yet." />

			<template v-else>
				<VisitCard
					v-for="visit in history.data.value"
					:key="visit.name"
					:visit="visit"
					with-date
				/>
			</template>
		</ScreenBody>
	</div>
</template>

<script setup>
import { LoadingIndicator } from "frappe-ui"

import EmptyState from "../components/EmptyState.vue"
import ErrorState from "../components/ErrorState.vue"
import PageHeader from "../components/PageHeader.vue"
import ScreenBody from "../components/ScreenBody.vue"
import VisitCard from "../components/VisitCard.vue"
import { api } from "../data/api"
import { useAsync } from "../data/useAsync"

const history = useAsync(() => api.myVisitHistory(50))
</script>

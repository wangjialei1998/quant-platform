<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { getTaskStatus } from '@/api/tasks'

const props = defineProps<{ taskId?: string }>()
const status = ref('')
const result = ref<unknown>(null)
let timer: number | undefined

const formattedResult = computed(() => {
  if (result.value === null || result.value === undefined) return ''
  if (typeof result.value === 'string') return result.value
  return JSON.stringify(result.value, null, 2)
})

async function refresh() {
  if (!props.taskId) return
  const response = await getTaskStatus(props.taskId)
  status.value = response.status
  result.value = response.result
  if (['success', 'failure', 'failed', 'revoked'].includes(response.status)) {
    window.clearInterval(timer)
  }
}

watch(
  () => props.taskId,
  (taskId) => {
    window.clearInterval(timer)
    status.value = ''
    result.value = null
    if (taskId) {
      refresh()
      timer = window.setInterval(refresh, 2000)
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <el-alert v-if="taskId" :closable="false" type="info" show-icon>
    <template #title>
      任务 {{ taskId }}：{{ status || 'pending' }}
    </template>
    <pre v-if="formattedResult" class="task-result">{{ formattedResult }}</pre>
  </el-alert>
</template>

<style scoped>
.task-result {
  max-height: 140px;
  overflow: auto;
  margin: 8px 0 0;
  white-space: pre-wrap;
}
</style>

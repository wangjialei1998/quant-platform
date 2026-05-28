<script setup lang="ts">
defineProps<{ logs?: string }>()
</script>

<template>
  <pre class="log-panel">{{ logs || '暂无日志' }}</pre>
</template>

<style scoped>
.log-panel {
  max-height: 280px;
  overflow: auto;
  padding: 12px;
  border-radius: 6px;
  background: #0f172a;
  color: #dbeafe;
}
</style>


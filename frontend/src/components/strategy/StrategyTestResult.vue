<script setup lang="ts">
defineProps<{ status?: string; log?: string }>()
</script>

<template>
  <el-alert :title="status || 'pending'" :closable="false" />
  <pre>{{ log || '暂无测试日志' }}</pre>
</template>


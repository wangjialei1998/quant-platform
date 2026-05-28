<script setup lang="ts">
import BaseChart from './BaseChart.vue'

defineProps<{ option: Record<string, unknown> }>()
</script>

<template>
  <BaseChart :option="option" />
</template>


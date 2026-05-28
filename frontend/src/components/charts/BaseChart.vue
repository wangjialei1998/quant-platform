<script setup lang="ts">
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  option: echarts.EChartsOption
  height?: number
}>()

const root = ref<HTMLDivElement>()
let chart: echarts.ECharts | undefined

function render() {
  if (!root.value) return
  if (!chart) {
    chart = echarts.init(root.value)
  }
  chart.setOption(props.option, true)
}

function resize() {
  chart?.resize()
}

watch(() => props.option, render, { deep: true })

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})
</script>

<template>
  <div ref="root" class="chart" :style="{ height: `${height ?? 340}px` }" />
</template>

<style scoped>
.chart {
  width: 100%;
}
</style>


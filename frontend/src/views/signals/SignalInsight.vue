<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import type { EChartsOption } from 'echarts'
import {
  getSignalDistribution,
  getSignalEffectiveness,
  getSignalFrequency,
  getSignalPriceChart,
  getSignalRisks,
  getSignalVolatility,
} from '@/api/signals'
import BaseChart from '@/components/charts/BaseChart.vue'

const route = useRoute()
const portfolioId = Number(route.params.id)
const distribution = ref<Record<string, unknown>>({})
const effectiveness = ref<Record<string, unknown>>({})
const frequency = ref<Record<string, unknown>>({})
const risks = ref<Record<string, unknown>[]>([])
const normalized = ref(true)
const showSignals = ref(true)

const chartOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0 },
  grid: { top: 48, left: 48, right: 24, bottom: 48 },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  series: [{ name: '价格', type: 'line', data: [] }],
}))

async function load() {
  await getSignalPriceChart(portfolioId)
  await getSignalVolatility(portfolioId)
  distribution.value = await getSignalDistribution(portfolioId)
  effectiveness.value = await getSignalEffectiveness(portfolioId)
  frequency.value = await getSignalFrequency(portfolioId)
  risks.value = await getSignalRisks(portfolioId)
}

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">信号洞察</h1>
      <div class="toolbar">
        <el-checkbox v-model="showSignals">显示交易信号</el-checkbox>
        <el-checkbox v-model="normalized">标准化价格</el-checkbox>
      </div>
    </div>
    <el-card shadow="never" class="chart-panel">
      <template #header>策略信号洞察图</template>
      <BaseChart :option="chartOption" :height="380" />
    </el-card>
    <div class="metric-grid">
      <el-card shadow="never">
        <template #header>信号分布</template>
        <pre>{{ distribution }}</pre>
      </el-card>
      <el-card shadow="never">
        <template #header>信号有效性</template>
        <pre>{{ effectiveness }}</pre>
      </el-card>
      <el-card shadow="never">
        <template #header>交易频率</template>
        <pre>{{ frequency }}</pre>
      </el-card>
    </div>
    <el-card shadow="never">
      <template #header>风险信号</template>
      <el-empty v-if="!risks.length" description="暂无风险信号" />
      <el-table v-else :data="risks">
        <el-table-column prop="type" label="类型" />
        <el-table-column prop="level" label="等级" />
        <el-table-column prop="message" label="说明" />
      </el-table>
    </el-card>
  </section>
</template>

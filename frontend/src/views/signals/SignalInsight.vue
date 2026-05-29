<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import type { EChartsOption, SeriesOption } from 'echarts'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getSignalAnnualVolatility,
  getSignalDistribution,
  getSignalEffectiveness,
  getSignalFrequency,
  getSignalPriceChart,
  getSignalRisks,
  getSignalTradingFrequencyText,
  getSignalVolatility,
} from '@/api/signals'
import BaseChart from '@/components/charts/BaseChart.vue'

type PriceSeries = { name: string; data: [string, number][] }
type SignalPoint = { date: string; symbol: string; side: 'buy' | 'sell'; price: number }
type Effectiveness = {
  buy?: { count?: number; day_5?: number; day_20?: number; avg_return?: number }
  sell?: { count?: number; day_5?: number; day_20?: number; avg_return?: number }
}

const route = useRoute()
const router = useRouter()
const portfolioId = Number(route.params.id)
const distribution = ref<Record<string, number>>({})
const effectiveness = ref<Effectiveness>({})
const frequency = ref<Record<string, unknown>>({})
const frequencyText = ref({ summary: '', buy: '', sell: '' })
const risks = ref<Record<string, unknown>[]>([])
const annualVolatility = ref<{ symbol: string; name: string; annual_volatility: number }[]>([])
const priceChart = ref<{ dates: string[]; series: PriceSeries[]; signals: SignalPoint[] }>({
  dates: [],
  series: [],
  signals: [],
})
const volatilityChart = ref<{ months: string[]; series: { name: string; data: number[] }[] }>({
  months: [],
  series: [],
})
const normalized = ref(true)
const showSignals = ref(true)

const priceChartOption = computed<EChartsOption>(() => {
  const series: SeriesOption[] = priceChart.value.series.map((item) => {
    const points = priceChart.value.signals
      .filter((signal) => showSignals.value && signal.symbol === item.name)
      .map((signal) => {
        const y = findSignalY(item, signal.date)
        if (y === null) return null
        return {
          name: signal.side === 'buy' ? '买入' : '卖出',
          coord: [signal.date, y],
          value: signal.side === 'buy' ? 'B' : 'S',
          itemStyle: { color: signal.side === 'buy' ? '#16a34a' : '#dc2626' },
        }
      })
      .filter((point): point is { name: string; coord: [string, number]; value: string; itemStyle: { color: string } } => point !== null)

    return {
      name: item.name,
      type: 'line',
      smooth: true,
      symbol: 'none',
      data: item.data,
      markPoint: showSignals.value
        ? {
            symbol: 'pin',
            symbolSize: 44,
            label: { color: '#fff', fontWeight: 'bold' },
            data: points,
          }
        : undefined,
    }
  })

  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0 },
    grid: { top: 48, left: 48, right: 24, bottom: 54 },
    xAxis: { type: 'category', data: priceChart.value.dates },
    yAxis: { type: 'value' },
    dataZoom: [{ type: 'inside' }, { type: 'slider' }],
    series,
  }
})

const distributionOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'item' },
  series: [
    {
      name: '信号分布',
      type: 'pie',
      radius: ['45%', '72%'],
      data: [
        { name: '持仓', value: distribution.value.holding_days ?? 0, itemStyle: { color: '#2563eb' } },
        { name: '空仓', value: distribution.value.empty_days ?? 0, itemStyle: { color: '#94a3b8' } },
      ],
      label: { formatter: '{b}: {d}%' },
    },
  ],
}))

const effectivenessOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0 },
  grid: { top: 48, left: 44, right: 20, bottom: 36 },
  xAxis: { type: 'category', data: ['买入信号', '卖出信号'] },
  yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
  series: [
    {
      name: '5日有效性',
      type: 'bar',
      data: [effectiveness.value.buy?.day_5 ?? 0, effectiveness.value.sell?.day_5 ?? 0],
    },
    {
      name: '20日有效性',
      type: 'bar',
      data: [effectiveness.value.buy?.day_20 ?? 0, effectiveness.value.sell?.day_20 ?? 0],
    },
  ],
}))

const volatilityOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0 },
  grid: { top: 48, left: 48, right: 24, bottom: 48 },
  xAxis: { type: 'category', data: volatilityChart.value.months },
  yAxis: { type: 'value' },
  series: volatilityChart.value.series.map((item) => ({
    name: item.name,
    type: 'bar',
    data: item.data,
  })),
}))

const annualVolatilityOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', valueFormatter: (value) => `${Number(value).toFixed(2)}%` },
  grid: { top: 28, left: 56, right: 24, bottom: 42 },
  xAxis: { type: 'category', data: annualVolatility.value.map((item) => item.symbol) },
  yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
  series: [
    {
      name: '年化波动率',
      type: 'bar',
      data: annualVolatility.value.map((item) => Number((item.annual_volatility * 100).toFixed(2))),
      itemStyle: { color: '#7c3aed' },
    },
  ],
}))

function findSignalY(series: PriceSeries, date: string) {
  return series.data.find((point) => point[0] === date)?.[1] ?? null
}

function formatPercent(value?: number) {
  return `${Number(value ?? 0).toFixed(1)}%`
}

function formatReturn(value?: number) {
  return `${Number(value ?? 0).toFixed(2)}%`
}

async function load() {
  priceChart.value = await getSignalPriceChart(portfolioId)
  volatilityChart.value = await getSignalVolatility(portfolioId)
  annualVolatility.value = (await getSignalAnnualVolatility(portfolioId)).rows
  distribution.value = await getSignalDistribution(portfolioId)
  effectiveness.value = await getSignalEffectiveness(portfolioId)
  frequency.value = await getSignalFrequency(portfolioId)
  frequencyText.value = await getSignalTradingFrequencyText(portfolioId)
  risks.value = await getSignalRisks(portfolioId)
}

watch(normalized, load)
onMounted(load)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div class="toolbar">
        <el-button :icon="ArrowLeft" @click="router.push(`/portfolios/${portfolioId}`)">返回组合</el-button>
        <h1 class="page-title">信号洞察</h1>
      </div>
      <div class="toolbar">
        <el-checkbox v-model="showSignals">显示交易信号</el-checkbox>
        <el-checkbox v-model="normalized">标准化价格</el-checkbox>
      </div>
    </div>

    <el-card shadow="never" class="chart-panel">
      <template #header>策略信号洞察图</template>
      <BaseChart :option="priceChartOption" :height="400" />
    </el-card>

    <div class="insight-grid">
      <el-card shadow="never" class="chart-panel">
        <template #header>信号分布</template>
        <BaseChart :option="distributionOption" :height="280" />
      </el-card>
      <el-card shadow="never" class="chart-panel">
        <template #header>信号有效性</template>
        <BaseChart :option="effectivenessOption" :height="280" />
        <div class="effectiveness-text">
          <div>🟢 买入信号：5日 {{ formatPercent(effectiveness.buy?.day_5) }}，20日 {{ formatPercent(effectiveness.buy?.day_20) }}，均收益 {{ formatReturn(effectiveness.buy?.avg_return) }}</div>
          <div>🔴 卖出信号：5日 {{ formatPercent(effectiveness.sell?.day_5) }}，20日 {{ formatPercent(effectiveness.sell?.day_20) }}，均收益 {{ formatReturn(effectiveness.sell?.avg_return) }}</div>
        </div>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>交易频率</template>
      <div class="frequency-copy">
        <div>{{ frequencyText.summary }}</div>
        <div>🟢 {{ frequencyText.buy }}</div>
        <div>🔴 {{ frequencyText.sell }}</div>
        <div class="muted">
          总信号 {{ frequency.total ?? 0 }} 次，买入 {{ frequency.buy_count ?? 0 }} 次，卖出 {{ frequency.sell_count ?? 0 }} 次，平均间隔 {{ frequency.avg_interval_days ?? '-' }} 天。
        </div>
      </div>
    </el-card>

    <div class="insight-grid">
      <el-card shadow="never" class="chart-panel">
        <template #header>月度波动率</template>
        <BaseChart :option="volatilityOption" :height="320" />
      </el-card>
      <el-card shadow="never" class="chart-panel">
        <template #header>标的年化波动率</template>
        <BaseChart :option="annualVolatilityOption" :height="320" />
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

<style scoped>
.insight-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
}

.effectiveness-text,
.frequency-copy {
  display: grid;
  gap: 8px;
  margin-top: 12px;
  line-height: 1.7;
}
</style>

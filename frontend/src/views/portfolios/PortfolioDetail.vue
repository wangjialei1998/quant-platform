<script setup lang="ts">
import { ArrowLeft, Refresh, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { EChartsOption } from 'echarts'
import {
  getCashFlows,
  getDrawdown,
  getEquityCurve,
  getPortfolio,
  getPortfolioPerformance,
  getPortfolioSummary,
  getPositionValues,
  getReturnContribution,
  getPositions,
  getTrades,
  runPortfolio,
  updatePortfolioEmail,
  type Portfolio,
} from '@/api/portfolios'
import BaseChart from '@/components/charts/BaseChart.vue'
import TaskStatus from '@/components/common/TaskStatus.vue'
import MetricCards from '@/components/portfolio/MetricCards.vue'

const route = useRoute()
const router = useRouter()
const portfolioId = Number(route.params.id)
const portfolio = ref<Portfolio>()
const summary = ref<Record<string, unknown>>()
const trades = ref<Record<string, unknown>[]>([])
const positions = ref<Record<string, unknown>[]>([])
const cashFlows = ref<Record<string, unknown>[]>([])
const performance = ref({
  monthly: [] as { period: string; return: number; start_net_value: number; end_net_value: number }[],
  yearly: [] as { period: string; return: number; start_net_value: number; end_net_value: number }[],
})
const positionValues = ref({ dates: [] as string[], series: [] as { name: string; data: number[] }[] })
const returnContribution = ref({ period: 'month' as 'month' | 'year', series: [] as { symbol: string; contribution: number }[] })
const contributionPeriod = ref<'month' | 'year'>('month')
const contributionPeriodOptions = [
  { label: '月度', value: 'month' },
  { label: '年度', value: 'year' },
]
let loadingContribution = false
const taskId = ref('')
const equityCurve = ref({
  dates: [] as string[],
  portfolio: [] as number[],
  benchmark: [] as number[],
  trades: [] as { date: string; side: 'buy' | 'sell'; symbol: string; net_value: number | null }[],
})
const equityBenchmarks = [
  { name: '沪深300', annualReturn: 0.08, color: '#64748b' },
  { name: '中证500', annualReturn: 0.10, color: '#0f766e' },
  { name: '纳斯达克', annualReturn: 0.12, color: '#9333ea' },
  { name: '标普500', annualReturn: 0.10, color: '#ea580c' },
  { name: '15%基准', annualReturn: 0.15, color: '#dc2626' },
]
const drawdown = ref({ dates: [] as string[], drawdown: [] as number[] })
const emailEnabled = ref(false)

const equityOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0 },
  grid: { left: 48, right: 24, top: 48, bottom: 48 },
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  xAxis: { type: 'category', data: equityCurve.value.dates },
  yAxis: { type: 'value' },
  series: [
    {
      name: '组合净值',
      type: 'line',
      smooth: true,
      data: equityCurve.value.portfolio,
    },
    ...equityBenchmarks.map((benchmark) => ({
      name: benchmark.name,
      type: 'line' as const,
      smooth: true,
      symbol: 'none',
      lineStyle: { type: 'dashed' as const, color: benchmark.color },
      itemStyle: { color: benchmark.color },
      data: benchmarkCurve(benchmark.annualReturn),
    })),
  ],
}))

const drawdownOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 48, right: 24, top: 36, bottom: 48 },
  xAxis: { type: 'category', data: drawdown.value.dates },
  yAxis: { type: 'value' },
  series: [{ name: '回撤', type: 'line', areaStyle: {}, data: drawdown.value.drawdown }],
}))

const performanceOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', valueFormatter: (value) => `${(Number(value) * 100).toFixed(2)}%` },
  legend: { top: 0 },
  grid: { top: 48, left: 48, right: 24, bottom: 48 },
  xAxis: { type: 'category', data: performance.value.monthly.map((item) => item.period) },
  yAxis: { type: 'value', axisLabel: { formatter: (value: number) => `${(value * 100).toFixed(0)}%` } },
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  series: [
    {
      name: '月度收益',
      type: 'bar',
      data: performance.value.monthly.map((item) => item.return),
      itemStyle: { color: '#2563eb' },
    },
  ],
}))

const contributionOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 56, right: 24, top: 28, bottom: 42 },
  xAxis: { type: 'category', data: returnContribution.value.series.map((item) => item.symbol) },
  yAxis: { type: 'value' },
  series: [
    {
      name: contributionPeriod.value === 'month' ? '月度收益贡献' : '年度收益贡献',
      type: 'bar',
      data: returnContribution.value.series.map((item) => item.contribution),
      itemStyle: { color: '#0f766e' },
    },
  ],
}))

const positionValueOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0 },
  grid: { top: 48, left: 56, right: 24, bottom: 48 },
  xAxis: { type: 'category', data: positionValues.value.dates },
  yAxis: { type: 'value' },
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  series: positionValues.value.series.map((item) => ({
    name: item.name,
    type: 'line',
    areaStyle: {},
    data: item.data,
  })),
}))

async function load() {
  portfolio.value = await getPortfolio(portfolioId)
  summary.value = await getPortfolioSummary(portfolioId)
  emailEnabled.value = Boolean(summary.value.email_enabled)
  await loadEquityCurve()
  drawdown.value = await getDrawdown(portfolioId)
  trades.value = await getTrades(portfolioId)
  positions.value = await getPositions(portfolioId)
  cashFlows.value = await getCashFlows(portfolioId)
  performance.value = await getPortfolioPerformance(portfolioId)
  positionValues.value = await getPositionValues(portfolioId)
  await loadContribution()
}

async function loadEquityCurve() {
  equityCurve.value = await getEquityCurve(portfolioId)
}

async function loadContribution() {
  loadingContribution = true
  returnContribution.value = await getReturnContribution(portfolioId, contributionPeriod.value)
  loadingContribution = false
}

async function toggleEmail(value: boolean | string | number) {
  emailEnabled.value = Boolean(value)
  const response = await updatePortfolioEmail(portfolioId, emailEnabled.value)
  emailEnabled.value = response.email_enabled
}

async function run() {
  const response = await runPortfolio(portfolioId)
  taskId.value = response.task_id
  ElMessage.success('组合更新任务已提交')
}

watch(contributionPeriod, () => {
  if (!loadingContribution) loadContribution()
})
onMounted(load)

function benchmarkCurve(annualReturn: number) {
  return equityCurve.value.dates.map((_, index) => Number(((1 + annualReturn) ** (index / 252)).toFixed(6)))
}
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">{{ portfolio?.name ?? '组合详情' }}</h1>
      <div class="toolbar">
        <el-button :icon="ArrowLeft" @click="router.push('/portfolios')">返回</el-button>
        <span class="muted">邮件提醒</span>
        <el-switch v-model="emailEnabled" @change="toggleEmail" />
        <el-button :icon="TrendCharts" @click="router.push(`/portfolios/${portfolioId}/signals`)">信号洞察</el-button>
        <el-button type="primary" :icon="Refresh" @click="run">手动更新</el-button>
      </div>
    </div>
    <TaskStatus :task-id="taskId" />
    <MetricCards :summary="summary" />
    <el-card shadow="never" class="chart-panel">
      <template #header>
        <div class="chart-header">
          <span>盈利曲线</span>
        </div>
      </template>
      <BaseChart :option="equityOption" />
    </el-card>
    <el-card shadow="never" class="chart-panel">
      <template #header>回撤曲线</template>
      <BaseChart :option="drawdownOption" />
    </el-card>
    <div class="detail-grid">
      <el-card shadow="never" class="chart-panel">
        <template #header>月度表现</template>
        <BaseChart :option="performanceOption" />
      </el-card>
      <el-card shadow="never" class="chart-panel">
        <template #header>
          <div class="chart-header">
            <span>收益贡献</span>
            <el-segmented v-model="contributionPeriod" :options="contributionPeriodOptions" />
          </div>
        </template>
        <BaseChart :option="contributionOption" />
      </el-card>
    </div>
    <el-card shadow="never" class="chart-panel">
      <template #header>历史持仓金额变化</template>
      <BaseChart :option="positionValueOption" />
    </el-card>
    <el-tabs>
      <el-tab-pane label="年度表现">
        <el-table :data="performance.yearly">
          <el-table-column prop="period" label="年份" />
          <el-table-column prop="start_net_value" label="期初净值" />
          <el-table-column prop="end_net_value" label="期末净值" />
          <el-table-column label="收益率">
            <template #default="{ row }">{{ (Number(row.return) * 100).toFixed(2) }}%</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="月度表现">
        <el-table :data="performance.monthly">
          <el-table-column prop="period" label="月份" />
          <el-table-column prop="start_net_value" label="期初净值" />
          <el-table-column prop="end_net_value" label="期末净值" />
          <el-table-column label="收益率">
            <template #default="{ row }">{{ (Number(row.return) * 100).toFixed(2) }}%</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="历史交易">
        <el-table :data="trades">
          <el-table-column prop="trade_date" label="日期" />
          <el-table-column prop="symbol" label="标的" />
          <el-table-column prop="side" label="方向" />
          <el-table-column prop="quantity" label="数量" />
          <el-table-column prop="price" label="价格" />
          <el-table-column prop="net_amount" label="净金额" />
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="历史持仓">
        <el-table :data="positions">
          <el-table-column prop="date" label="日期" />
          <el-table-column prop="symbol" label="标的" />
          <el-table-column prop="quantity" label="数量" />
          <el-table-column prop="market_value" label="市值" />
          <el-table-column prop="weight" label="权重" />
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="资金流水">
        <el-table :data="cashFlows">
          <el-table-column prop="flow_date" label="日期" />
          <el-table-column prop="flow_type" label="类型" />
          <el-table-column prop="amount" label="变动金额" />
          <el-table-column prop="available_cash" label="可用资金" />
          <el-table-column prop="total_asset" label="总资产" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<style scoped>
.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
}
</style>

<script setup lang="ts">
import type { EChartsOption } from 'echarts'
import { ArrowLeft, Refresh, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref, watch, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getCashFlows,
  getDrawdown,
  getEquityCurve,
  getPortfolio,
  getPortfolioPerformance,
  getPortfolioSummary,
  getPositionValues,
  getPositions,
  getReturnContribution,
  getTrades,
  runPortfolio,
  updatePortfolioEmail,
  type InstrumentSeries,
  type Portfolio,
  type PositionRow,
  type ReturnContributionPayload,
  type TradeRow,
} from '@/api/portfolios'
import BaseChart from '@/components/charts/BaseChart.vue'
import TaskStatus from '@/components/common/TaskStatus.vue'
import MetricCards from '@/components/portfolio/MetricCards.vue'

type Period = 'month' | 'year'
type PerformanceItem = {
  period: string
  return: number
  start_net_value: number
  end_net_value: number
}

const route = useRoute()
const router = useRouter()
const portfolioId = Number(route.params.id)

const portfolio = ref<Portfolio>()
const summary = ref<Record<string, unknown>>()
const trades = ref<TradeRow[]>([])
const positions = ref<PositionRow[]>([])
const cashFlows = ref<Record<string, unknown>[]>([])
const performance = ref({
  monthly: [] as PerformanceItem[],
  yearly: [] as PerformanceItem[],
})
const positionValues = ref({ dates: [] as string[], series: [] as InstrumentSeries[] })
const instrumentContribution = ref<ReturnContributionPayload>(emptyContribution('month'))
const instrumentContributionPeriod = ref<Period>('month')
const assetContributionPeriod = ref<Period>('month')
const selectedContributionSymbols = ref<string[]>([])
const selectedPositionValueSymbols = ref<string[]>([])
const taskId = ref('')
const equityCurve = ref({
  dates: [] as string[],
  portfolio: [] as number[],
  benchmark: [] as (number | null)[],
  trades: [] as { date: string; side: 'buy' | 'sell'; symbol: string; instrument_name: string; net_value: number | null }[],
})
const equityBenchmarks = [
  { name: '沪深300', symbol: '000300.SH', color: '#64748b' },
  { name: '中证500', symbol: '000905.SH', color: '#0f766e' },
]
const benchmarkCurves = ref<Record<string, (number | null)[]>>({})
const fixedBenchmarks = [{ name: '15%基准', annualReturn: 0.15, color: '#dc2626' }]
const drawdown = ref({ dates: [] as string[], drawdown: [] as number[] })
const emailEnabled = ref(false)

const periodOptions = [
  { label: '月度', value: 'month' },
  { label: '年度', value: 'year' },
]

const contributionInstrumentOptions = computed(() => instrumentOptions(instrumentContribution.value.series))
const positionValueInstrumentOptions = computed(() => instrumentOptions(positionValues.value.series))
const filteredContributionSeries = computed(() =>
  instrumentContribution.value.series.filter((item) => selectedContributionSymbols.value.includes(item.symbol)),
)
const filteredPositionValueSeries = computed(() =>
  positionValues.value.series.filter((item) => selectedPositionValueSymbols.value.includes(item.symbol)),
)

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
      data: benchmarkCurves.value[benchmark.symbol] ?? [],
    })),
    ...fixedBenchmarks.map((benchmark) => ({
      name: benchmark.name,
      type: 'line' as const,
      smooth: true,
      symbol: 'none',
      lineStyle: { type: 'dashed' as const, color: benchmark.color },
      itemStyle: { color: benchmark.color },
      data: fixedBenchmarkCurve(benchmark.annualReturn),
    })),
  ],
}))

const drawdownOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', valueFormatter: percentFormatter },
  grid: { left: 48, right: 24, top: 36, bottom: 48 },
  xAxis: { type: 'category', data: drawdown.value.dates },
  yAxis: { type: 'value', axisLabel: { formatter: (value: number) => percentFormatter(value) } },
  series: [{ name: '回撤', type: 'line', areaStyle: {}, data: drawdown.value.drawdown }],
}))

const instrumentContributionOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', valueFormatter: percentFormatter },
  legend: { top: 0, type: 'scroll' },
  grid: { top: 52, left: 56, right: 24, bottom: 54 },
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  xAxis: { type: 'category', data: instrumentContribution.value.periods },
  yAxis: { type: 'value', axisLabel: { formatter: (value: number) => percentFormatter(value) } },
  series: filteredContributionSeries.value.map((item) => ({
    name: item.name,
    type: 'bar',
    data: item.data,
  })),
}))

const selectedPerformance = computed(() =>
  assetContributionPeriod.value === 'month' ? performance.value.monthly : performance.value.yearly,
)

const assetContributionOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis', valueFormatter: percentFormatter },
  grid: { top: 36, left: 56, right: 24, bottom: 54 },
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  xAxis: { type: 'category', data: selectedPerformance.value.map((item) => item.period) },
  yAxis: { type: 'value', axisLabel: { formatter: (value: number) => percentFormatter(value) } },
  series: [
    {
      name: assetContributionPeriod.value === 'month' ? '月度总资产贡献率' : '年度总资产贡献率',
      type: 'bar',
      data: selectedPerformance.value.map((item) => item.return),
      itemStyle: { color: '#2563eb' },
    },
  ],
}))

const positionValueOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0, type: 'scroll' },
  grid: { top: 48, left: 56, right: 24, bottom: 48 },
  xAxis: { type: 'category', data: positionValues.value.dates },
  yAxis: { type: 'value' },
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  series: filteredPositionValueSeries.value.map((item) => ({
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
  syncSelectedSymbols(selectedPositionValueSymbols, positionValues.value.series)
  await loadInstrumentContribution()
}

async function loadEquityCurve() {
  equityCurve.value = await getEquityCurve(portfolioId)
  const benchmarkResponses = await Promise.all(
    equityBenchmarks.map(async (benchmark) => ({
      symbol: benchmark.symbol,
      payload: await getEquityCurve(portfolioId, benchmark.symbol),
    })),
  )
  benchmarkCurves.value = Object.fromEntries(
    benchmarkResponses.map((item) => [item.symbol, item.payload.benchmark]),
  )
}

async function loadInstrumentContribution() {
  instrumentContribution.value = await getReturnContribution(portfolioId, instrumentContributionPeriod.value)
  syncSelectedSymbols(selectedContributionSymbols, instrumentContribution.value.series)
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

watch(instrumentContributionPeriod, loadInstrumentContribution)
onMounted(load)

function fixedBenchmarkCurve(annualReturn: number) {
  return equityCurve.value.dates.map((_, index) => Number(((1 + annualReturn) ** (index / 252)).toFixed(6)))
}

function emptyContribution(period: Period): ReturnContributionPayload {
  return { period, periods: [], symbols: [], names: [], series: [] }
}

function percentFormatter(value: unknown) {
  return `${(Number(value || 0) * 100).toFixed(2)}%`
}

function instrumentOptions(series: InstrumentSeries[]) {
  return series.map((item) => ({ label: item.name || item.symbol, value: item.symbol }))
}

function syncSelectedSymbols(selection: Ref<string[]>, series: InstrumentSeries[]) {
  const symbols = series.map((item) => item.symbol)
  const validSymbols = new Set(symbols)
  const selected = selection.value.filter((symbol) => validSymbols.has(symbol))
  selection.value = selected.length ? selected : symbols
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
      <template #header>盈利曲线</template>
      <BaseChart :option="equityOption" />
    </el-card>

    <el-card shadow="never" class="chart-panel">
      <template #header>回撤曲线</template>
      <BaseChart :option="drawdownOption" />
    </el-card>

    <div class="detail-grid">
      <el-card shadow="never" class="chart-panel">
        <template #header>
          <div class="chart-header">
            <div class="chart-title-row">
              <span>{{ instrumentContributionPeriod === 'month' ? '月度收益贡献表' : '年度收益贡献表' }}</span>
              <el-segmented v-model="instrumentContributionPeriod" :options="periodOptions" />
            </div>
            <el-checkbox-group v-model="selectedContributionSymbols" class="instrument-filter">
              <el-checkbox
                v-for="item in contributionInstrumentOptions"
                :key="item.value"
                :value="item.value"
              >
                {{ item.label }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </template>
        <BaseChart :option="instrumentContributionOption" />
      </el-card>

      <el-card shadow="never" class="chart-panel">
        <template #header>
          <div class="chart-header">
            <span>年/月度收益表</span>
            <el-segmented v-model="assetContributionPeriod" :options="periodOptions" />
          </div>
        </template>
        <BaseChart :option="assetContributionOption" />
      </el-card>
    </div>

    <el-card shadow="never" class="chart-panel">
      <template #header>
        <div class="chart-header">
          <span>历史持仓金额变化</span>
          <el-checkbox-group v-model="selectedPositionValueSymbols" class="instrument-filter">
            <el-checkbox
              v-for="item in positionValueInstrumentOptions"
              :key="item.value"
              :value="item.value"
            >
              {{ item.label }}
            </el-checkbox>
          </el-checkbox-group>
        </div>
      </template>
      <BaseChart :option="positionValueOption" />
    </el-card>

    <el-tabs>
      <el-tab-pane label="年度表现">
        <el-table :data="performance.yearly">
          <el-table-column prop="period" label="年份" />
          <el-table-column prop="start_net_value" label="期初净值" />
          <el-table-column prop="end_net_value" label="期末净值" />
          <el-table-column label="收益率">
            <template #default="{ row }">{{ percentFormatter(row.return) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="月度表现">
        <el-table :data="performance.monthly">
          <el-table-column prop="period" label="月份" />
          <el-table-column prop="start_net_value" label="期初净值" />
          <el-table-column prop="end_net_value" label="期末净值" />
          <el-table-column label="收益率">
            <template #default="{ row }">{{ percentFormatter(row.return) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="历史交易">
        <el-table :data="trades">
          <el-table-column prop="trade_date" label="日期" />
          <el-table-column prop="instrument_name" label="标的" />
          <el-table-column prop="side" label="方向" />
          <el-table-column prop="quantity" label="数量" />
          <el-table-column prop="price" label="价格" />
          <el-table-column prop="net_amount" label="净金额" />
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="历史持仓">
        <el-table :data="positions">
          <el-table-column prop="date" label="日期" />
          <el-table-column prop="instrument_name" label="标的" />
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
  flex-wrap: wrap;
  gap: 12px;
}

.chart-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.instrument-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  max-width: 100%;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px;
}
</style>

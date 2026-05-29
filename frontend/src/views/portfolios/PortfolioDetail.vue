<script setup lang="ts">
import { ArrowLeft, Refresh, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { EChartsOption } from 'echarts'
import {
  getCashFlows,
  getDrawdown,
  getEquityCurve,
  getPortfolio,
  getPortfolioSummary,
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
const taskId = ref('')
const equityCurve = ref({
  dates: [] as string[],
  portfolio: [] as number[],
  benchmark: [] as number[],
  trades: [] as { date: string; side: 'buy' | 'sell'; symbol: string; net_value: number | null }[],
})
const drawdown = ref({ dates: [] as string[], drawdown: [] as number[] })
const benchmark = ref('')
const emailEnabled = ref(false)

const equityOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 48, right: 24, top: 36, bottom: 48 },
  dataZoom: [{ type: 'inside' }, { type: 'slider' }],
  xAxis: { type: 'category', data: equityCurve.value.dates },
  yAxis: { type: 'value' },
  series: [
    {
      name: '组合净值',
      type: 'line',
      smooth: true,
      data: equityCurve.value.portfolio,
      markPoint: {
        symbol: 'pin',
        symbolSize: 46,
        label: { color: '#fff', fontWeight: 'bold' },
        data: (equityCurve.value.trades ?? [])
          .filter((trade): trade is { date: string; side: 'buy' | 'sell'; symbol: string; net_value: number } => trade.net_value !== null)
          .map((trade) => ({
            name: trade.side === 'buy' ? '买入' : '卖出',
            coord: [trade.date, trade.net_value],
            value: trade.side === 'buy' ? 'B' : 'S',
            itemStyle: { color: trade.side === 'buy' ? '#16a34a' : '#dc2626' },
          })),
      },
    },
    ...(benchmark.value
      ? [
          {
            name: benchmark.value,
            type: 'line' as const,
            smooth: true,
            lineStyle: { type: 'dashed' as const },
            data: equityCurve.value.benchmark,
          },
        ]
      : []),
  ],
}))

const drawdownOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 48, right: 24, top: 36, bottom: 48 },
  xAxis: { type: 'category', data: drawdown.value.dates },
  yAxis: { type: 'value' },
  series: [{ name: '回撤', type: 'line', areaStyle: {}, data: drawdown.value.drawdown }],
}))

async function load() {
  portfolio.value = await getPortfolio(portfolioId)
  summary.value = await getPortfolioSummary(portfolioId)
  emailEnabled.value = Boolean(summary.value.email_enabled)
  equityCurve.value = await getEquityCurve(portfolioId)
  drawdown.value = await getDrawdown(portfolioId)
  trades.value = await getTrades(portfolioId)
  positions.value = await getPositions(portfolioId)
  cashFlows.value = await getCashFlows(portfolioId)
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

onMounted(load)
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
          <el-select v-model="benchmark" clearable placeholder="选择对比基准" style="width: 180px">
            <el-option label="沪深300" value="沪深300" />
          </el-select>
        </div>
      </template>
      <BaseChart :option="equityOption" />
    </el-card>
    <el-card shadow="never" class="chart-panel">
      <template #header>回撤曲线</template>
      <BaseChart :option="drawdownOption" />
    </el-card>
    <el-tabs>
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
</style>

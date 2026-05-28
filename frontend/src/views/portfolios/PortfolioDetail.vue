<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
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
  type Portfolio,
} from '@/api/portfolios'
import BaseChart from '@/components/charts/BaseChart.vue'
import TaskStatus from '@/components/common/TaskStatus.vue'
import MetricCards from '@/components/portfolio/MetricCards.vue'

const route = useRoute()
const portfolioId = Number(route.params.id)
const portfolio = ref<Portfolio>()
const summary = ref<Record<string, unknown>>()
const trades = ref<Record<string, unknown>[]>([])
const positions = ref<Record<string, unknown>[]>([])
const cashFlows = ref<Record<string, unknown>[]>([])
const taskId = ref('')

const emptyChart = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: [] }],
}))

async function load() {
  portfolio.value = await getPortfolio(portfolioId)
  summary.value = await getPortfolioSummary(portfolioId)
  await getEquityCurve(portfolioId)
  await getDrawdown(portfolioId)
  trades.value = await getTrades(portfolioId)
  positions.value = await getPositions(portfolioId)
  cashFlows.value = await getCashFlows(portfolioId)
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
      <el-button type="primary" :icon="Refresh" @click="run">手动更新</el-button>
    </div>
    <TaskStatus :task-id="taskId" />
    <MetricCards :summary="summary" />
    <el-card shadow="never" class="chart-panel">
      <template #header>收益曲线</template>
      <BaseChart :option="emptyChart" />
    </el-card>
    <el-tabs>
      <el-tab-pane label="历史交易">
        <el-table :data="trades">
          <el-table-column prop="trade_date" label="日期" />
          <el-table-column prop="instrument_id" label="标的" />
          <el-table-column prop="side" label="方向" />
          <el-table-column prop="quantity" label="数量" />
          <el-table-column prop="price" label="价格" />
          <el-table-column prop="net_amount" label="净金额" />
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="历史持仓">
        <el-table :data="positions">
          <el-table-column prop="date" label="日期" />
          <el-table-column prop="instrument_id" label="标的" />
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

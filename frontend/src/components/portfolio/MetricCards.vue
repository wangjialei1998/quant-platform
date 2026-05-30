<script setup lang="ts">
const props = defineProps<{ summary?: Record<string, unknown> }>()

function numberValue(key: string) {
  return Number(props.summary?.[key] ?? 0)
}

function plain(key: string, fallback: string | number = '-') {
  return props.summary?.[key] ?? fallback
}

function percent(key: string, digits = 2) {
  return `${(numberValue(key) * 100).toFixed(digits)}%`
}

function decimal(key: string, digits = 4) {
  return numberValue(key).toFixed(digits)
}

const metrics = [
  { label: '最新净值', value: () => decimal('latest_net_value', 4) },
  { label: '年复合收益率', value: () => percent('annual_return') },
  { label: '胜率', value: () => percent('win_rate') },
  { label: '盈亏比', value: () => decimal('profit_loss_ratio', 2) },
  { label: '夏普比', value: () => decimal('sharpe_ratio', 2) },
  { label: '当前回撤', value: () => percent('current_drawdown') },
  { label: '最大回撤', value: () => percent('max_drawdown') },
  { label: '最大回撤时间', value: () => `${plain('max_drawdown_days', 0)} 天` },
  { label: '波动率', value: () => percent('volatility') },
  { label: 'SQN', value: () => decimal('sqn', 2) },
  { label: 'VWR', value: () => `${decimal('vwr', 2)}%` },
  { label: '总交易次数', value: () => plain('trade_count', 0) },
  { label: '运行天数', value: () => `${plain('running_days', 0)} 天` },
  { label: '建仓日期', value: () => plain('start_date') },
  { label: '更新日期', value: () => plain('updated_at') },
]
</script>

<template>
  <div class="metric-grid detail-metrics">
    <el-card v-for="item in metrics" :key="item.label" shadow="never" class="metric-card">
      <div class="muted">{{ item.label }}</div>
      <strong>{{ item.value() }}</strong>
    </el-card>
  </div>
</template>

<style scoped>
.detail-metrics {
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

.metric-card strong {
  display: block;
  margin-top: 6px;
  font-size: 18px;
  line-height: 1.3;
  word-break: break-word;
}
</style>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createInstrument } from '@/api/instruments'
import { getPortfolioEdit, updatePortfolio } from '@/api/portfolios'
import { listStrategies, type Strategy } from '@/api/strategies'
import InstrumentSelector from '@/components/common/InstrumentSelector.vue'
import TaskStatus from '@/components/common/TaskStatus.vue'

const route = useRoute()
const router = useRouter()
const portfolioId = Number(route.params.id)
const strategies = ref<Strategy[]>([])
const taskId = ref('')
const loading = ref(false)
const form = reactive({
  name: '',
  strategy_id: undefined as number | undefined,
  instrument_ids: [] as number[],
  initial_cash: '',
  start_date: '',
  email_enabled: true,
  commission_rate: '',
  stamp_tax_rate: '',
  slippage_rate: '',
})
const instrumentForm = reactive({
  symbol: '',
})
const selectorKey = ref(0)

async function load() {
  loading.value = true
  try {
    const [portfolio, strategyRows] = await Promise.all([
      getPortfolioEdit(portfolioId),
      listStrategies(),
    ])
    strategies.value = strategyRows
    form.name = portfolio.name
    form.strategy_id = portfolio.strategy_id
    form.instrument_ids = [...portfolio.instrument_ids]
    form.initial_cash = String(portfolio.initial_cash)
    form.start_date = portfolio.start_date
    form.email_enabled = portfolio.email_enabled
    form.commission_rate = String(portfolio.commission_rate ?? '')
    form.stamp_tax_rate = String(portfolio.stamp_tax_rate ?? '')
    form.slippage_rate = String(portfolio.slippage_rate ?? '')
    selectorKey.value += 1
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.strategy_id) return
  await ElMessageBox.confirm('保存修改后会清理该组合已有回测结果，并从起始日期重新回测到当前最近交易日。继续？', '确认重新回测', {
    type: 'warning',
  })
  const response = await updatePortfolio(portfolioId, {
    name: form.name,
    strategy_id: form.strategy_id,
    instrument_ids: form.instrument_ids,
    initial_cash: form.initial_cash,
    start_date: form.start_date,
    email_enabled: form.email_enabled,
    commission_rate: form.commission_rate || undefined,
    stamp_tax_rate: form.stamp_tax_rate || undefined,
    slippage_rate: form.slippage_rate || undefined,
  })
  taskId.value = response.task_id
  ElMessage.success('组合修改已保存，重新回测任务已提交')
  router.push('/portfolios')
}

async function addInstrument() {
  const symbol = instrumentForm.symbol.trim()
  if (!symbol) return
  const instrument = await createInstrument({ symbol })
  if (!form.instrument_ids.includes(instrument.id)) {
    form.instrument_ids.push(instrument.id)
  }
  selectorKey.value += 1
  instrumentForm.symbol = ''
  ElMessage.success('标的已添加')
}

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">修改组合</h1>
      <div class="toolbar">
        <el-button :icon="ArrowLeft" @click="router.push('/portfolios')">返回</el-button>
        <el-button type="primary" @click="submit">保存并重新回测</el-button>
      </div>
    </div>
    <TaskStatus :task-id="taskId" />
    <el-card v-loading="loading" shadow="never">
      <el-form label-width="100px">
        <el-form-item label="组合名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="策略">
          <el-select v-model="form.strategy_id" filterable style="width: 100%">
            <el-option v-for="item in strategies" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标的">
          <InstrumentSelector :key="selectorKey" v-model="form.instrument_ids" />
        </el-form-item>
        <el-form-item label="新增标的">
          <div class="instrument-inline">
            <el-input v-model="instrumentForm.symbol" placeholder="代码，如 510300" />
            <el-button @click="addInstrument">添加</el-button>
          </div>
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input v-model="form.initial_cash" />
        </el-form-item>
        <el-form-item label="起始日期">
          <el-date-picker v-model="form.start_date" value-format="YYYY-MM-DD" type="date" style="width: 100%" />
        </el-form-item>
        <el-form-item label="邮件提醒">
          <el-switch v-model="form.email_enabled" />
        </el-form-item>
        <el-form-item label="交易参数">
          <div class="fee-grid">
            <el-input v-model="form.commission_rate" placeholder="佣金率，默认 0.0003" />
            <el-input v-model="form.stamp_tax_rate" placeholder="印花税率，默认 0.001" />
            <el-input v-model="form.slippage_rate" placeholder="滑点率，默认 0.0002" />
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </section>
</template>

<style scoped>
.instrument-inline {
  display: grid;
  width: 100%;
  grid-template-columns: minmax(180px, 320px) auto;
  gap: 8px;
}

.fee-grid {
  display: grid;
  width: 100%;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px;
}
</style>

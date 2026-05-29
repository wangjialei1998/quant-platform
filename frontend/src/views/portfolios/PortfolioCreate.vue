<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createInstrument } from '@/api/instruments'
import { createPortfolio } from '@/api/portfolios'
import { listStrategies, type Strategy } from '@/api/strategies'
import InstrumentSelector from '@/components/common/InstrumentSelector.vue'
import TaskStatus from '@/components/common/TaskStatus.vue'

const router = useRouter()
const strategies = ref<Strategy[]>([])
const taskId = ref('')
const form = reactive({
  name: '',
  strategy_id: undefined as number | undefined,
  instrument_ids: [] as number[],
  initial_cash: '1000000',
  start_date: '',
  email_enabled: true,
})
const instrumentForm = reactive({
  symbol: '',
})
const selectorKey = ref(0)

async function submit() {
  if (!form.strategy_id) return
  const response = await createPortfolio({
    ...form,
    strategy_id: form.strategy_id,
  })
  taskId.value = response.task_id
  ElMessage.success('组合创建任务已提交')
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

onMounted(async () => {
  strategies.value = await listStrategies()
})
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">创建组合</h1>
      <div class="toolbar">
        <el-button :icon="ArrowLeft" @click="router.push('/portfolios')">返回</el-button>
        <el-button type="primary" @click="submit">创建并回测</el-button>
      </div>
    </div>
    <TaskStatus :task-id="taskId" />
    <el-card shadow="never">
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
</style>

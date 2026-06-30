<script setup lang="ts">
import { Delete, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import {
  deleteMarketDailyBars,
  getMarketDailyBars,
  getMarketDataRanges,
  syncMarketDataCacheToToday,
} from '@/api/marketData'
import TaskStatus from '@/components/common/TaskStatus.vue'

const loading = ref(false)
const ranges = ref<Record<string, unknown>[]>([])
const bars = ref<Record<string, unknown>[]>([])
const selectedRange = ref<Record<string, unknown> | null>(null)
const queryRange = ref<[string, string] | null>(null)
const syncTaskId = ref('')

async function load() {
  loading.value = true
  try {
    ranges.value = await getMarketDataRanges()
  } finally {
    loading.value = false
  }
}

async function remove(row: Record<string, unknown>) {
  if (!row.start_date || !row.end_date) return
  await ElMessageBox.confirm(`删除 ${row.symbol} 的已缓存日线数据？`, '确认删除', { type: 'warning' })
  await deleteMarketDailyBars({
    instrument_id: row.instrument_id,
    start_date: row.start_date,
    end_date: row.end_date,
  })
  ElMessage.success('缓存已删除')
  await load()
}

async function viewBars(row: Record<string, unknown>) {
  selectedRange.value = row
  const startDate = queryRange.value?.[0] || row.start_date
  const endDate = queryRange.value?.[1] || row.end_date
  bars.value = (await getMarketDailyBars({
    instrument_id: row.instrument_id,
    start_date: startDate,
    end_date: endDate,
  })) as Record<string, unknown>[]
}

async function syncCache() {
  const response = await syncMarketDataCacheToToday()
  syncTaskId.value = response.task_id
  ElMessage.success('行情缓存同步任务已提交')
}

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">行情缓存管理</h1>
      <div class="toolbar">
        <el-button type="primary" :icon="Refresh" @click="syncCache">同步到今日</el-button>
        <el-button :icon="Refresh" @click="load">刷新</el-button>
      </div>
    </div>
    <TaskStatus :task-id="syncTaskId" />
    <el-card shadow="never">
      <el-table v-loading="loading" :data="ranges">
        <el-table-column prop="symbol" label="代码" width="140" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="start_date" label="开始日期" width="140" />
        <el-table-column prop="end_date" label="结束日期" width="140" />
        <el-table-column prop="bar_count" label="数据条数" width="120" />
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button text @click="viewBars(row)">查看</el-button>
            <el-button :icon="Delete" text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-card shadow="never">
      <template #header>
        <div class="cache-header">
          <span>日线数据检查</span>
          <div class="toolbar">
            <el-date-picker
              v-model="queryRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
            />
            <el-button :disabled="!selectedRange" @click="selectedRange && viewBars(selectedRange)">查询</el-button>
          </div>
        </div>
      </template>
      <el-empty v-if="!selectedRange" description="选择一个标的查看缓存日线" />
      <el-table v-else :data="bars" height="360">
        <el-table-column prop="trade_date" label="日期" width="120" />
        <el-table-column prop="open" label="开盘" />
        <el-table-column prop="high" label="最高" />
        <el-table-column prop="low" label="最低" />
        <el-table-column prop="close" label="收盘" />
        <el-table-column prop="volume" label="成交量" />
        <el-table-column prop="adjustment_type" label="复权" width="90" />
      </el-table>
    </el-card>
  </section>
</template>

<style scoped>
.cache-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
</style>

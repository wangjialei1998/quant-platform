<script setup lang="ts">
import { Delete, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { deleteMarketDailyBars, getMarketDataRanges } from '@/api/marketData'

const loading = ref(false)
const ranges = ref<Record<string, unknown>[]>([])

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

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">行情缓存管理</h1>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
    </div>
    <el-card shadow="never">
      <el-table v-loading="loading" :data="ranges">
        <el-table-column prop="symbol" label="代码" width="140" />
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="start_date" label="开始日期" width="140" />
        <el-table-column prop="end_date" label="结束日期" width="140" />
        <el-table-column prop="bar_count" label="数据条数" width="120" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button :icon="Delete" text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </section>
</template>


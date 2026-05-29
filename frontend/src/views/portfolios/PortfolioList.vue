<script setup lang="ts">
import { Delete, Plus, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  deletePortfolio,
  listPortfolios,
  pausePortfolio,
  resumePortfolio,
  runPortfolio,
  type Portfolio,
} from '@/api/portfolios'
import TaskStatus from '@/components/common/TaskStatus.vue'

const router = useRouter()
const loading = ref(false)
const portfolios = ref<Portfolio[]>([])
const taskId = ref('')

async function load() {
  loading.value = true
  try {
    portfolios.value = await listPortfolios()
  } finally {
    loading.value = false
  }
}

async function run(row: Portfolio) {
  const response = await runPortfolio(row.id)
  taskId.value = response.task_id
  ElMessage.success('组合更新任务已提交')
}

async function toggle(row: Portfolio) {
  if (row.status === 'paused') {
    await resumePortfolio(row.id)
  } else {
    await pausePortfolio(row.id)
  }
  await load()
}

async function remove(row: Portfolio) {
  await ElMessageBox.confirm(`删除组合“${row.name}”及其回测、交易、持仓、资金流水、信号和日志数据？`, '确认删除', {
    type: 'warning',
  })
  await deletePortfolio(row.id)
  ElMessage.success('组合已删除')
  await load()
}

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">组合管理</h1>
      <div class="toolbar">
        <el-button :icon="Refresh" @click="load">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="router.push('/portfolios/new')">创建组合</el-button>
      </div>
    </div>
    <TaskStatus :task-id="taskId" />
    <el-card shadow="never">
      <el-table v-loading="loading" :data="portfolios">
        <el-table-column prop="name" label="组合名称" min-width="160" />
        <el-table-column prop="initial_cash" label="初始资金" width="130" />
        <el-table-column prop="start_date" label="起始日期" width="130" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="last_run_at" label="最近运行" width="190" />
        <el-table-column label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <el-button text @click="router.push(`/portfolios/${row.id}`)">详情</el-button>
            <el-button text @click="router.push(`/portfolios/${row.id}/signals`)">信号洞察</el-button>
            <el-button :icon="VideoPlay" text @click="run(row)">更新</el-button>
            <el-button text @click="toggle(row)">{{ row.status === 'paused' ? '恢复' : '暂停' }}</el-button>
            <el-button :icon="Delete" text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </section>
</template>

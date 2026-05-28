<script setup lang="ts">
import { Delete, Edit, Plus, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { deleteStrategy, listStrategies, testStrategy, type Strategy } from '@/api/strategies'
import TaskStatus from '@/components/common/TaskStatus.vue'

const router = useRouter()
const loading = ref(false)
const strategies = ref<Strategy[]>([])
const taskId = ref('')

async function load() {
  loading.value = true
  try {
    strategies.value = await listStrategies()
  } finally {
    loading.value = false
  }
}

async function submitTest(row: Strategy) {
  const response = await testStrategy(row.id)
  taskId.value = response.task_id
  ElMessage.success('策略测试任务已提交')
}

async function remove(row: Strategy) {
  await ElMessageBox.confirm(`删除策略 ${row.name}？`, '确认删除', { type: 'warning' })
  await deleteStrategy(row.id)
  await load()
}

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">策略管理</h1>
      <el-button type="primary" :icon="Plus" @click="router.push('/strategies/new')">新增策略</el-button>
    </div>
    <TaskStatus :task-id="taskId" />
    <el-card shadow="never">
      <el-table v-loading="loading" :data="strategies">
        <el-table-column prop="name" label="策略名称" min-width="160" />
        <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
        <el-table-column prop="test_status" label="测试状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.test_status === 'passed' ? 'success' : row.test_status === 'failed' ? 'danger' : 'info'">
              {{ row.test_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="190" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button :icon="Edit" text @click="router.push(`/strategies/${row.id}`)">详情</el-button>
            <el-button :icon="VideoPlay" text @click="submitTest(row)">测试</el-button>
            <el-button :icon="Delete" text type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </section>
</template>


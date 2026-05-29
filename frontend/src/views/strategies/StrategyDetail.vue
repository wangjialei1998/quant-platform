<script setup lang="ts">
import { ArrowLeft, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getStrategy, testStrategy, type Strategy } from '@/api/strategies'
import TaskStatus from '@/components/common/TaskStatus.vue'

const route = useRoute()
const router = useRouter()
const strategy = ref<Strategy>()
const taskId = ref('')

async function load() {
  strategy.value = await getStrategy(Number(route.params.id))
}

async function submitTest() {
  if (!strategy.value) return
  const response = await testStrategy(strategy.value.id)
  taskId.value = response.task_id
  ElMessage.success('策略测试任务已提交')
}

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <div class="toolbar">
        <el-button :icon="ArrowLeft" @click="router.push('/strategies')">返回策略列表</el-button>
        <h1 class="page-title">{{ strategy?.name ?? '策略详情' }}</h1>
      </div>
      <div class="toolbar">
        <el-button type="primary" :icon="VideoPlay" @click="submitTest">运行测试</el-button>
      </div>
    </div>
    <TaskStatus :task-id="taskId" />
    <el-descriptions v-if="strategy" :column="2" border>
      <el-descriptions-item label="描述">{{ strategy.description || '-' }}</el-descriptions-item>
      <el-descriptions-item label="测试状态">{{ strategy.test_status }}</el-descriptions-item>
      <el-descriptions-item label="代码路径">{{ strategy.code_path }}</el-descriptions-item>
      <el-descriptions-item label="代码哈希">{{ strategy.code_hash }}</el-descriptions-item>
    </el-descriptions>
    <el-card shadow="never">
      <template #header>策略代码</template>
      <el-input :model-value="strategy?.code || ''" type="textarea" :rows="24" readonly class="code-viewer" />
    </el-card>
    <el-card shadow="never">
      <template #header>最近测试日志</template>
      <pre>{{ strategy?.test_log || '暂无日志' }}</pre>
    </el-card>
  </section>
</template>

<style scoped>
.code-viewer :deep(textarea) {
  font-family: "Cascadia Code", Consolas, monospace;
  line-height: 1.55;
}
</style>

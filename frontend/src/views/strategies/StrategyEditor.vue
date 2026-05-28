<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { createStrategy } from '@/api/strategies'

const router = useRouter()
const form = reactive({
  name: '',
  description: '',
  code: `import backtrader as bt


class DemoStrategy(bt.Strategy):
    def next(self):
        pass
`,
})

async function submit() {
  const strategy = await createStrategy(form)
  ElMessage.success('策略已保存')
  router.push(`/strategies/${strategy.id}`)
}
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">新增策略</h1>
      <el-button type="primary" @click="submit">保存策略</el-button>
    </div>
    <el-card shadow="never">
      <el-form label-width="96px">
        <el-form-item label="策略名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="策略代码">
          <el-input v-model="form.code" type="textarea" :rows="22" class="code-input" />
        </el-form-item>
      </el-form>
    </el-card>
  </section>
</template>

<style scoped>
.code-input :deep(textarea) {
  font-family: "Cascadia Code", Consolas, monospace;
}
</style>


<script setup lang="ts">
import { Message, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, ref } from 'vue'
import { getEmailSettings, testEmailSettings } from '@/api/settings'

const settings = ref<Record<string, unknown>>({})

async function load() {
  settings.value = await getEmailSettings()
}

async function testEmail() {
  await testEmailSettings()
  ElMessage.success('测试邮件任务接口已调用')
}

onMounted(load)
</script>

<template>
  <section class="page">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
      <el-button :icon="Refresh" @click="load">刷新</el-button>
    </div>
    <el-card shadow="never">
      <template #header>邮件配置</template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="SMTP Host">{{ settings.smtp_host || '-' }}</el-descriptions-item>
        <el-descriptions-item label="SMTP Port">{{ settings.smtp_port || '-' }}</el-descriptions-item>
        <el-descriptions-item label="发件人">{{ settings.smtp_from || '-' }}</el-descriptions-item>
        <el-descriptions-item label="收件人">{{ settings.smtp_to || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="settings.configured ? 'success' : 'info'">
            {{ settings.configured ? '已配置' : '未配置' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <div class="toolbar setting-actions">
        <el-button type="primary" :icon="Message" @click="testEmail">发送测试邮件</el-button>
      </div>
    </el-card>
  </section>
</template>

<style scoped>
.setting-actions {
  margin-top: 16px;
}
</style>


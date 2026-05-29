<script setup lang="ts">
import { Message, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { onMounted, reactive, ref } from 'vue'
import { getEmailSettings, testEmailSettings, updateEmailSettings } from '@/api/settings'

const settings = ref<Record<string, unknown>>({})
const form = reactive({
  smtp_host: '',
  smtp_port: 587,
  smtp_username: '',
  smtp_password: '',
  smtp_from: '',
  smtp_to: '',
})

async function load() {
  settings.value = await getEmailSettings()
  form.smtp_host = String(settings.value.smtp_host ?? '')
  form.smtp_port = Number(settings.value.smtp_port ?? 587)
  form.smtp_username = String(settings.value.smtp_username ?? '')
  form.smtp_from = String(settings.value.smtp_from ?? '')
  form.smtp_to = String(settings.value.smtp_to ?? '')
}

async function save() {
  await updateEmailSettings({
    ...form,
    smtp_password: form.smtp_password || undefined,
  })
  ElMessage.success('邮件配置已更新')
  await load()
}

async function testEmail() {
  await testEmailSettings()
  ElMessage.success('测试邮件已发送')
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
      <el-form class="settings-form" label-width="110px">
        <el-form-item label="SMTP Host">
          <el-input v-model="form.smtp_host" />
        </el-form-item>
        <el-form-item label="SMTP Port">
          <el-input-number v-model="form.smtp_port" :min="1" :max="65535" style="width: 100%" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="form.smtp_username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.smtp_password" type="password" show-password placeholder="留空则不修改" />
        </el-form-item>
        <el-form-item label="发件人">
          <el-input v-model="form.smtp_from" />
        </el-form-item>
        <el-form-item label="收件人">
          <el-input v-model="form.smtp_to" />
        </el-form-item>
      </el-form>
      <div class="toolbar setting-actions">
        <el-button @click="save">保存配置</el-button>
        <el-button type="primary" :icon="Message" @click="testEmail">发送测试邮件</el-button>
      </div>
    </el-card>
  </section>
</template>

<style scoped>
.setting-actions {
  margin-top: 16px;
}

.settings-form {
  max-width: 680px;
  margin-top: 18px;
}
</style>

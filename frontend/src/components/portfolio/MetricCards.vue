<script setup lang="ts">
defineProps<{ summary?: Record<string, unknown> }>()
</script>

<template>
  <div class="metric-grid">
    <el-card shadow="never">
      <div class="muted">最新净值</div>
      <strong>{{ summary?.latest_net_value ?? '1.0000' }}</strong>
    </el-card>
    <el-card shadow="never">
      <div class="muted">累计收益</div>
      <strong>{{ summary?.total_return ?? '0.00%' }}</strong>
    </el-card>
    <el-card shadow="never">
      <div class="muted">最大回撤</div>
      <strong>{{ summary?.max_drawdown ?? '0.00%' }}</strong>
    </el-card>
    <el-card shadow="never">
      <div class="muted">交易次数</div>
      <strong>{{ summary?.trade_count ?? 0 }}</strong>
    </el-card>
  </div>
</template>


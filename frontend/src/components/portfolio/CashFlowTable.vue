<script setup lang="ts">
defineProps<{ rows: Record<string, unknown>[] }>()
</script>

<template>
  <el-table :data="rows">
    <el-table-column prop="flow_date" label="日期" />
    <el-table-column prop="flow_type" label="类型" />
    <el-table-column prop="amount" label="金额" />
    <el-table-column prop="total_asset" label="总资产" />
  </el-table>
</template>


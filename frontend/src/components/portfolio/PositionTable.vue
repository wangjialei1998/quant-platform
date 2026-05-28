<script setup lang="ts">
defineProps<{ rows: Record<string, unknown>[] }>()
</script>

<template>
  <el-table :data="rows">
    <el-table-column prop="date" label="日期" />
    <el-table-column prop="instrument_id" label="标的" />
    <el-table-column prop="quantity" label="数量" />
    <el-table-column prop="market_value" label="市值" />
  </el-table>
</template>


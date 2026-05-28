<script setup lang="ts">
defineProps<{ rows: Record<string, unknown>[] }>()
</script>

<template>
  <el-table :data="rows">
    <el-table-column prop="trade_date" label="日期" />
    <el-table-column prop="side" label="方向" />
    <el-table-column prop="quantity" label="数量" />
    <el-table-column prop="price" label="价格" />
  </el-table>
</template>


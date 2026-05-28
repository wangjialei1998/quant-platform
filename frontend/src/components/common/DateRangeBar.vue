<script setup lang="ts">
const model = defineModel<[string, string] | undefined>()
</script>

<template>
  <el-date-picker
    v-model="model"
    type="daterange"
    value-format="YYYY-MM-DD"
    start-placeholder="开始日期"
    end-placeholder="结束日期"
  />
</template>


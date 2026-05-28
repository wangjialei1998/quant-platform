<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listInstruments, type Instrument } from '@/api/instruments'

const model = defineModel<number[]>({ default: [] })
const instruments = ref<Instrument[]>([])

onMounted(async () => {
  instruments.value = await listInstruments()
})
</script>

<template>
  <el-select v-model="model" multiple filterable placeholder="选择股票或 ETF" style="width: 100%">
    <el-option
      v-for="item in instruments"
      :key="item.id"
      :label="`${item.symbol} ${item.name}`"
      :value="item.id"
    />
  </el-select>
</template>


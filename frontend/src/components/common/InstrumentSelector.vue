<script setup lang="ts">
import { ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { computed, onMounted, ref } from 'vue'
import { listInstruments, type Instrument } from '@/api/instruments'

const model = defineModel<number[]>({ default: [] })
const instruments = ref<Instrument[]>([])
const instrumentMap = computed(() => new Map(instruments.value.map((item) => [item.id, item])))
const orderedSelected = computed(() =>
  model.value.map((id) => instrumentMap.value.get(id) ?? {
    id,
    symbol: String(id),
    name: '',
    instrument_type: 'stock' as const,
    exchange: '',
    is_active: true,
  }),
)

function moveSelected(index: number, direction: -1 | 1) {
  const target = index + direction
  if (target < 0 || target >= model.value.length) return
  const next = [...model.value]
  ;[next[index], next[target]] = [next[target], next[index]]
  model.value = next
}

onMounted(async () => {
  instruments.value = await listInstruments()
})
</script>

<template>
  <div class="instrument-selector">
    <el-select v-model="model" multiple filterable placeholder="选择股票或 ETF" style="width: 100%">
      <el-option
        v-for="item in instruments"
        :key="item.id"
        :label="`${item.symbol} ${item.name}`"
        :value="item.id"
      />
    </el-select>
    <div v-if="orderedSelected.length" class="selected-order">
      <div v-for="(item, index) in orderedSelected" :key="item.id" class="selected-row">
        <span class="order-index">{{ index + 1 }}</span>
        <span class="selected-name">{{ item.symbol }} {{ item.name }}</span>
        <el-button :icon="ArrowUp" circle size="small" :disabled="index === 0" @click="moveSelected(index, -1)" />
        <el-button
          :icon="ArrowDown"
          circle
          size="small"
          :disabled="index === orderedSelected.length - 1"
          @click="moveSelected(index, 1)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.instrument-selector {
  width: 100%;
}

.selected-order {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}

.selected-row {
  display: grid;
  grid-template-columns: 32px 1fr 28px 28px;
  align-items: center;
  gap: 8px;
}

.order-index {
  color: #64748b;
  font-size: 12px;
  text-align: center;
}

.selected-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

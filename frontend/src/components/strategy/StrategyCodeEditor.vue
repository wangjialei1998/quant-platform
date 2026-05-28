<script setup lang="ts">
const model = defineModel<string>({ default: '' })
</script>

<template>
  <el-input v-model="model" type="textarea" :rows="22" class="code-editor" />
</template>

<style scoped>
.code-editor :deep(textarea) {
  font-family: "Cascadia Code", Consolas, monospace;
}
</style>


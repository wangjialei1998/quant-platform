import { defineStore } from 'pinia'

export const useTaskStore = defineStore('task', {
  state: () => ({
    latestTaskId: '',
  }),
  actions: {
    setTask(taskId: string) {
      this.latestTaskId = taskId
    },
  },
})


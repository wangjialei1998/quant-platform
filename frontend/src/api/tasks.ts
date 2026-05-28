import { http, unwrap } from './http'

export function getTaskStatus(taskId: string) {
  return unwrap(http.get<{ task_id: string; status: string; result?: unknown }>(`/tasks/${taskId}`))
}

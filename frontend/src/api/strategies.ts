import { http, unwrap } from './http'

export interface Strategy {
  id: number
  name: string
  description?: string
  code_path: string
  code_hash: string
  test_status: string
  test_log?: string
  code?: string
  last_tested_at?: string
  created_at: string
  updated_at: string
}

export interface StrategyCreate {
  name: string
  description?: string
  code: string
}

export function listStrategies() {
  return unwrap(http.get<Strategy[]>('/strategies'))
}

export function getStrategy(id: number) {
  return unwrap(http.get<Strategy>(`/strategies/${id}`))
}

export function createStrategy(payload: StrategyCreate) {
  return unwrap(http.post<Strategy>('/strategies', payload))
}

export function testStrategy(id: number) {
  return unwrap(http.post<{ task_id: string; status: string }>(`/strategies/${id}/test`))
}

export function deleteStrategy(id: number) {
  return unwrap(http.delete(`/strategies/${id}`))
}

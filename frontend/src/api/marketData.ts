import { http, unwrap } from './http'

export function getMarketDataRanges() {
  return unwrap(http.get<Record<string, unknown>[]>('/market-data/ranges'))
}

export function getMarketDailyBars(params: Record<string, unknown>) {
  return unwrap(http.get('/market-data/bars', { params }))
}

export function deleteMarketDailyBars(params: Record<string, unknown>) {
  return unwrap(http.delete('/market-data/bars', { params }))
}

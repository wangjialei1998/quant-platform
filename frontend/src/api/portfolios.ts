import { http, unwrap } from './http'

export interface Portfolio {
  id: number
  name: string
  strategy_id: number
  initial_cash: string
  start_date: string
  status: string
  email_enabled: boolean
  commission_rate: string
  stamp_tax_rate: string
  slippage_rate: string
  last_run_at?: string
  created_at: string
  updated_at: string
  strategy_name?: string
  instrument_count?: number
  latest_net_value?: number
  current_total_asset?: string
  total_return?: number
  max_drawdown?: number
  latest_metric_date?: string
}

export interface PortfolioCreate {
  name: string
  strategy_id: number
  instrument_ids: number[]
  initial_cash: string
  start_date: string
  email_enabled: boolean
  commission_rate?: string
  stamp_tax_rate?: string
  slippage_rate?: string
}

export interface PortfolioEditPayload extends PortfolioCreate {}

export interface PortfolioEditData extends PortfolioCreate {
  id: number
  status: string
  commission_rate: string
  stamp_tax_rate: string
  slippage_rate: string
}

export function listPortfolios() {
  return unwrap(http.get<Portfolio[]>('/portfolios'))
}

export function getPortfolio(id: number) {
  return unwrap(http.get<Portfolio>(`/portfolios/${id}`))
}

export function getPortfolioEdit(id: number) {
  return unwrap(http.get<PortfolioEditData>(`/portfolios/${id}/edit`))
}

export function createPortfolio(payload: PortfolioCreate) {
  return unwrap(http.post<{ task_id: string; status: string }>('/portfolios', payload))
}

export function updatePortfolio(id: number, payload: PortfolioEditPayload) {
  return unwrap(http.patch<{ task_id: string; status: string }>(`/portfolios/${id}`, payload))
}

export function pausePortfolio(id: number) {
  return unwrap(http.post<Portfolio>(`/portfolios/${id}/pause`))
}

export function resumePortfolio(id: number) {
  return unwrap(http.post<Portfolio>(`/portfolios/${id}/resume`))
}

export function runPortfolio(id: number) {
  return unwrap(http.post<{ task_id: string; status: string }>(`/portfolios/${id}/run`))
}

export function deletePortfolio(id: number) {
  return unwrap(http.delete<{ message: string }>(`/portfolios/${id}`))
}

export function getPortfolioSummary(id: number) {
  return unwrap(http.get<Record<string, unknown>>(`/portfolios/${id}/summary`))
}

export function updatePortfolioEmail(id: number, emailEnabled: boolean) {
  return unwrap(http.patch<{ message: string; email_enabled: boolean }>(`/portfolios/${id}/email`, null, {
    params: { email_enabled: emailEnabled },
  }))
}

export interface EquityCurvePayload {
  dates: string[]
  portfolio: number[]
  benchmark: (number | null)[]
  trades: { date: string; side: 'buy' | 'sell'; symbol: string; net_value: number | null }[]
}

export interface DrawdownPayload {
  dates: string[]
  drawdown: number[]
}

export function getEquityCurve(id: number, benchmarkSymbol?: string) {
  return unwrap(
    http.get<EquityCurvePayload>(`/portfolios/${id}/equity-curve`, {
      params: benchmarkSymbol ? { benchmark_symbol: benchmarkSymbol } : undefined,
    }),
  )
}

export function getDrawdown(id: number) {
  return unwrap(http.get<DrawdownPayload>(`/portfolios/${id}/drawdown`))
}

export function getTrades(id: number) {
  return unwrap(http.get<[]>(`/portfolios/${id}/trades`))
}

export function getPositions(id: number) {
  return unwrap(http.get<[]>(`/portfolios/${id}/positions`))
}

export function getCashFlows(id: number) {
  return unwrap(http.get<[]>(`/portfolios/${id}/cash-flows`))
}

export function getPortfolioPerformance(id: number) {
  return unwrap(
    http.get<{
      monthly: { period: string; start_net_value: number; end_net_value: number; return: number }[]
      yearly: { period: string; start_net_value: number; end_net_value: number; return: number }[]
    }>(`/portfolios/${id}/performance`),
  )
}

export function getPositionValues(id: number) {
  return unwrap(http.get<{ dates: string[]; series: { name: string; data: number[] }[] }>(`/portfolios/${id}/position-values`))
}

export interface ReturnContributionPayload {
  period: 'month' | 'year'
  periods: string[]
  symbols: string[]
  series: { symbol: string; data: number[] }[]
}

export function getReturnContribution(id: number, period: 'month' | 'year') {
  return unwrap(http.get<ReturnContributionPayload>(`/portfolios/${id}/return-contribution`, { params: { period } }))
}

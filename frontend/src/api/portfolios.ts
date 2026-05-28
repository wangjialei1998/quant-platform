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
}

export interface PortfolioCreate {
  name: string
  strategy_id: number
  instrument_ids: number[]
  initial_cash: string
  start_date: string
  email_enabled: boolean
}

export function listPortfolios() {
  return unwrap(http.get<Portfolio[]>('/portfolios'))
}

export function getPortfolio(id: number) {
  return unwrap(http.get<Portfolio>(`/portfolios/${id}`))
}

export function createPortfolio(payload: PortfolioCreate) {
  return unwrap(http.post<{ task_id: string; status: string }>('/portfolios', payload))
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

export function getPortfolioSummary(id: number) {
  return unwrap(http.get<Record<string, unknown>>(`/portfolios/${id}/summary`))
}

export function getEquityCurve(id: number) {
  return unwrap(http.get(`/portfolios/${id}/equity-curve`))
}

export function getDrawdown(id: number) {
  return unwrap(http.get(`/portfolios/${id}/drawdown`))
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

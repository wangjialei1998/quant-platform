import { http, unwrap } from './http'

export function getSignalPriceChart(portfolioId: number) {
  return unwrap(http.get(`/portfolios/${portfolioId}/signals/price-chart`))
}

export function getSignalDistribution(portfolioId: number) {
  return unwrap(http.get<Record<string, unknown>>(`/portfolios/${portfolioId}/signals/distribution`))
}

export function getSignalEffectiveness(portfolioId: number) {
  return unwrap(http.get<Record<string, unknown>>(`/portfolios/${portfolioId}/signals/effectiveness`))
}

export function getSignalFrequency(portfolioId: number) {
  return unwrap(http.get<Record<string, unknown>>(`/portfolios/${portfolioId}/signals/frequency`))
}

export function getSignalRisks(portfolioId: number) {
  return unwrap(http.get<Record<string, unknown>[]>(`/portfolios/${portfolioId}/signals/risks`))
}

export function getSignalVolatility(portfolioId: number) {
  return unwrap(http.get(`/portfolios/${portfolioId}/signals/volatility`))
}

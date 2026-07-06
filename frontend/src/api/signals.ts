import { http, unwrap } from './http'

export function getSignalPriceChart(portfolioId: number) {
  return unwrap(
    http.get<{
      dates: string[]
      series: { symbol: string; name: string; data: [string, number][] }[]
      signals: { date: string; symbol: string; name: string; side: 'buy' | 'sell'; price: number }[]
    }>(
      `/portfolios/${portfolioId}/signals/price-chart`,
    ),
  )
}

export function getSignalDistribution(portfolioId: number) {
  return unwrap(http.get<Record<string, number>>(`/portfolios/${portfolioId}/signals/distribution`))
}

export function getSignalEffectiveness(portfolioId: number) {
  return unwrap(http.get<Record<string, unknown>>(`/portfolios/${portfolioId}/signals/effectiveness`))
}

export function getSignalFrequency(portfolioId: number) {
  return unwrap(http.get<Record<string, unknown>>(`/portfolios/${portfolioId}/signals/frequency`))
}

export function getSignalTradingFrequencyText(portfolioId: number) {
  return unwrap(http.get<{ summary: string; buy: string; sell: string }>(`/portfolios/${portfolioId}/signals/trading-frequency-text`))
}

export function getSignalRisks(portfolioId: number) {
  return unwrap(http.get<Record<string, unknown>[]>(`/portfolios/${portfolioId}/signals/risks`))
}

export function getSignalVolatility(portfolioId: number) {
  return unwrap(http.get<{ months: string[]; series: { symbol: string; name: string; data: number[] }[] }>(`/portfolios/${portfolioId}/signals/volatility`))
}

export function getSignalAnnualVolatility(portfolioId: number) {
  return unwrap(http.get<{ rows: { symbol: string; name: string; annual_volatility: number }[] }>(`/portfolios/${portfolioId}/signals/annual-volatility`))
}

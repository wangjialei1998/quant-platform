import { http, unwrap } from './http'

export interface Instrument {
  id: number
  symbol: string
  name: string
  instrument_type: 'stock' | 'etf' | 'index'
  exchange: string
  is_active: boolean
}

export function listInstruments() {
  return unwrap(http.get<Instrument[]>('/instruments'))
}

export function createInstrument(payload: Omit<Instrument, 'id'>) {
  return unwrap(http.post<Instrument>('/instruments', payload))
}

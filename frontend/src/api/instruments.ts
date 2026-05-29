import { http, unwrap } from './http'

export interface Instrument {
  id: number
  symbol: string
  name: string
  instrument_type: 'stock' | 'etf' | 'index'
  exchange: string
  is_active: boolean
}

export interface InstrumentCreatePayload {
  symbol: string
  name?: string
  instrument_type?: 'stock' | 'etf' | 'index'
  exchange?: string
  is_active?: boolean
}

export function listInstruments() {
  return unwrap(http.get<Instrument[]>('/instruments'))
}

export function createInstrument(payload: InstrumentCreatePayload) {
  return unwrap(http.post<Instrument>('/instruments', payload))
}

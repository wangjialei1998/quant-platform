import { http, unwrap } from './http'

export function getEmailSettings() {
  return unwrap(http.get<Record<string, unknown>>('/settings/email'))
}

export function testEmailSettings() {
  return unwrap(http.post('/settings/email/test'))
}

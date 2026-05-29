import { http, unwrap } from './http'

export function getEmailSettings() {
  return unwrap(http.get<Record<string, unknown>>('/settings/email'))
}

export function updateEmailSettings(payload: Record<string, unknown>) {
  return unwrap(http.patch<Record<string, unknown>>('/settings/email', payload))
}

export function testEmailSettings() {
  return unwrap(http.post('/settings/email/test'))
}

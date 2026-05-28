import axios, { type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

export const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail ?? error.response?.data?.error?.message ?? error.message
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export type ApiPromise<T> = Promise<T>

export function unwrap<T>(promise: Promise<AxiosResponse<T>>): ApiPromise<T> {
  return promise as unknown as ApiPromise<T>
}

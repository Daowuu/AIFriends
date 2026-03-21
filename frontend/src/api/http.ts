import axios from 'axios'

import { pinia } from '@/stores'
import { useUserStore } from '@/stores/user'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  timeout: 5000,
})

let isRefreshing = false
let refreshSubscribers: Array<(token?: string, error?: unknown) => void> = []

const subscribeTokenRefresh = (callback: (token?: string, error?: unknown) => void) => {
  refreshSubscribers.push(callback)
}

const resolveTokenRefresh = (token?: string, error?: unknown) => {
  refreshSubscribers.forEach((callback) => callback(token, error))
  refreshSubscribers = []
}

api.interceptors.request.use((config) => {
  const user = useUserStore(pinia)

  if (user.accessToken) {
    config.headers.Authorization = `Bearer ${user.accessToken}`
  }

  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const user = useUserStore(pinia)
    const originalRequest = error?.config

    if (!originalRequest) {
      return Promise.reject(error)
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      return new Promise((resolve, reject) => {
        subscribeTokenRefresh((token, refreshError) => {
          if (refreshError || !token) {
            reject(refreshError || error)
            return
          }

          originalRequest.headers.Authorization = `Bearer ${token}`
          resolve(api(originalRequest))
        })

        if (!isRefreshing) {
          isRefreshing = true

          axios.post(
            '/api/user/account/refresh_token/',
            {},
            { withCredentials: true, timeout: 5000 },
          ).then((response) => {
            user.setAccessToken(response.data.access)
            resolveTokenRefresh(response.data.access)
          }).catch((refreshError) => {
            user.clearAuth()
            resolveTokenRefresh(undefined, refreshError)
          }).finally(() => {
            isRefreshing = false
          })
        }
      })
    }

    return Promise.reject(error)
  },
)

export default api

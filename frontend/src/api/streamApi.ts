import { fetchEventSource } from '@microsoft/fetch-event-source'

import { pinia } from '@/stores'
import { useUserStore } from '@/stores/user'

type StreamPayload = {
  url: string
  body: Record<string, unknown>
  onmessage: (json: { content?: string; error?: string; meta?: Record<string, unknown> }, done: boolean) => void
  onerror?: (error: unknown) => void
  signal?: AbortSignal
}

export default async function streamApi(payload: StreamPayload) {
  const user = useUserStore(pinia)

  while (true) {
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      }

      if (user.accessToken) {
        headers.Authorization = `Bearer ${user.accessToken}`
      }

      await fetchEventSource(`/api${payload.url}`, {
        method: 'POST',
        signal: payload.signal,
        headers,
        body: JSON.stringify(payload.body),
        openWhenHidden: true,
        async onopen(response) {
          if (response.status === 401) {
            if (!user.accessToken) {
              throw new Error('当前会话未登录，请先登录后再继续。')
            }
            await user.refreshToken()
            throw new Error('TOKEN_REFRESHED')
          }

          if (!response.ok || !response.headers.get('content-type')?.includes('text/event-stream')) {
            const errorData = await response.json().catch(() => ({}))
            throw new Error(errorData.detail || `请求失败: ${response.status}`)
          }
        },
        onmessage(message) {
          if (message.data === '[DONE]') {
            payload.onmessage({}, true)
            return
          }

          try {
            payload.onmessage(JSON.parse(message.data), false)
          } catch (error) {
            payload.onerror?.(error)
          }
        },
        onerror(error) {
          throw error
        },
      })

      return
    } catch (error) {
      if (payload.signal?.aborted) {
        return
      }

      if (error instanceof Error && error.message === 'TOKEN_REFRESHED') {
        continue
      }

      payload.onerror?.(error)
      throw error
    }
  }
}

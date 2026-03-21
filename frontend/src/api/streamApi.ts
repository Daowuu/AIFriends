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
      await fetchEventSource(`/api${payload.url}`, {
        method: 'POST',
        signal: payload.signal,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user.accessToken}`,
        },
        body: JSON.stringify(payload.body),
        openWhenHidden: true,
        async onopen(response) {
          if (response.status === 401) {
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

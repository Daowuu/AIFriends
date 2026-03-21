<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import api from '@/api/http'
import streamApi from '@/api/streamApi'
import type { Character } from '@/types/character'
import type { ChatMessage } from '@/types/message'

import ChatHistory from './chat_history/ChatHistory.vue'
import InputField from './input_field/InputField.vue'

const props = withDefaults(defineProps<{
  character: Character | null
  pending?: boolean
  canManageFriend?: boolean
}>(), {
  pending: false,
  canManageFriend: false,
})

const messages = ref<ChatMessage[]>([])
const historyOffset = ref(0)
const hasMoreHistory = ref(true)
const loadingHistory = ref(false)
const sendingMessage = ref(false)
const isReplySpeaking = ref(false)
const chatError = ref('')
const inputResetToken = ref(0)
const chatHistoryRef = ref<InstanceType<typeof ChatHistory> | null>(null)
const inputRef = ref<InstanceType<typeof InputField> | null>(null)
let activeStreamController: AbortController | null = null
let activeAssistantMessageId: string | null = null
let speechPlaybackToken = 0
let activeAudio: HTMLAudioElement | null = null
let activeAudioUrl = ''

const EMOJI_PRESENTATION_REGEX = /[\p{Extended_Pictographic}\uFE0F]/gu
const EMOTICON_TOKEN_REGEX = /(\^[_-]?\^|T[_-]?T|QAQ|QAQ|qwq|QwQ|owo|OwO|uwu|UwU|XD|xD|哈哈哈+|呵呵呵+|[><][._-]?[<>()]|:\)|:-\)|:\(|:-\(|:D|:-D|;\)|;-\)|:\||:-\||\/::\)|\/::~|\/:B-|\/:8-\)|\/:<|\/:>|\/:\||\/:@|\/:P|\/:D|\/:\$|\/:X|\/:Z|\/:'\(|\/:Q|<3)+/gi
const BRACKET_EMOTE_REGEX = /[\[({（【]\s*(?:捂脸|偷笑|流汗|害羞|大笑|微笑|难过|委屈|尴尬|赞|鼓掌|哭笑|doge|笑哭|疑问|惊讶|发呆|生气|叹气|无语|撇嘴|呲牙|色|可爱|亲亲|比心)\s*[\])}）】]/gi

const stopAudioPlayback = () => {
  speechPlaybackToken += 1
  isReplySpeaking.value = false
  if (activeAudio) {
    activeAudio.onplay = null
    activeAudio.onended = null
    activeAudio.onerror = null
    activeAudio.pause()
    activeAudio.src = ''
    activeAudio.load()
    activeAudio = null
  }
  if (activeAudioUrl && typeof URL !== 'undefined') {
    URL.revokeObjectURL(activeAudioUrl)
    activeAudioUrl = ''
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel()
  }
}

const normalizeSpeechText = (text: string) => {
  return text
    .replace(/```[\s\S]*?```/g, '。')
    .replace(/`[^`]*`/g, '。')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/https?:\/\/\S+/g, '这个链接')
    .replace(BRACKET_EMOTE_REGEX, '。')
    .replace(EMOTICON_TOKEN_REGEX, '。')
    .replace(EMOJI_PRESENTATION_REGEX, '')
    .replace(/[~～]{2,}/g, '。')
    .replace(/[!！]{2,}/g, '！')
    .replace(/[?？]{2,}/g, '？')
    .replace(/\.{3,}/g, '。')
    .replace(/[、,，]{3,}/g, '，')
    .replace(/\s+/g, ' ')
    .replace(/([。！？]){2,}/g, '$1')
    .replace(/[（(][^（）()]{0,12}[)）]/g, ' ')
    .trim()
}

const playBrowserSpeech = (speechText: string, playbackToken: number) => {
  if (typeof window === 'undefined' || !('speechSynthesis' in window) || typeof SpeechSynthesisUtterance === 'undefined') {
    if (speechPlaybackToken === playbackToken) {
      void inputRef.value?.resumeLiveListening()
    }
    return
  }

  const utterance = new SpeechSynthesisUtterance(speechText)
  utterance.lang = 'zh-CN'
  utterance.rate = 1
  utterance.onstart = () => {
    if (speechPlaybackToken !== playbackToken) return
    isReplySpeaking.value = true
  }
  utterance.onend = () => {
    if (speechPlaybackToken !== playbackToken) return
    isReplySpeaking.value = false
    void inputRef.value?.resumeLiveListening()
  }
  utterance.onerror = () => {
    if (speechPlaybackToken !== playbackToken) return
    isReplySpeaking.value = false
    void inputRef.value?.resumeLiveListening()
  }
  window.speechSynthesis.speak(utterance)
}

const playBackendSpeech = async (speechText: string, playbackToken: number) => {
  if (!props.character?.friend_id) {
    throw new Error('当前聊天会话不存在。')
  }

  const response = await api.post(
    '/friend/message/tts/',
    {
      friend_id: props.character.friend_id,
      text: speechText,
    },
    {
      responseType: 'blob',
      timeout: 20000,
    },
  )

  const blob = response.data instanceof Blob ? response.data : new Blob([response.data], { type: 'audio/mpeg' })
  if (!blob.size) {
    throw new Error('语音合成没有返回有效音频。')
  }

  activeAudioUrl = URL.createObjectURL(blob)
  const audio = new Audio(activeAudioUrl)
  activeAudio = audio
  audio.preload = 'auto'
  audio.onplay = () => {
    if (speechPlaybackToken !== playbackToken) return
    isReplySpeaking.value = true
  }
  audio.onended = () => {
    if (speechPlaybackToken !== playbackToken) return
    isReplySpeaking.value = false
    activeAudio = null
    if (activeAudioUrl && typeof URL !== 'undefined') {
      URL.revokeObjectURL(activeAudioUrl)
      activeAudioUrl = ''
    }
    void inputRef.value?.resumeLiveListening()
  }
  audio.onerror = () => {
    if (speechPlaybackToken !== playbackToken) return
    isReplySpeaking.value = false
    activeAudio = null
    if (activeAudioUrl && typeof URL !== 'undefined') {
      URL.revokeObjectURL(activeAudioUrl)
      activeAudioUrl = ''
    }
    void inputRef.value?.resumeLiveListening()
  }

  await audio.play()
}

const speakReply = async (text: string) => {
  const speechText = normalizeSpeechText(text)
  if (!speechText) return
  if (!inputRef.value?.isVoiceMode()) return

  inputRef.value?.pauseLiveListening()
  stopAudioPlayback()
  const playbackToken = speechPlaybackToken

  try {
    await playBackendSpeech(speechText, playbackToken)
  } catch {
    playBrowserSpeech(speechText, playbackToken)
  }
}

const appendMessage = (message: ChatMessage) => {
  messages.value = [...messages.value, message]
}

const stopCurrentReply = ({ clearError = false } = {}) => {
  const interruptedSpeechPlayback = isReplySpeaking.value
  activeStreamController?.abort()
  activeStreamController = null
  stopAudioPlayback()

  if (activeAssistantMessageId) {
    const currentAssistant = messages.value.find((item) => item.id === activeAssistantMessageId)
    if (!currentAssistant?.content.trim()) {
      messages.value = messages.value.filter((item) => item.id !== activeAssistantMessageId)
    }
  }

  activeAssistantMessageId = null
  sendingMessage.value = false

  if (clearError) {
    chatError.value = ''
  }

  if (interruptedSpeechPlayback) {
    void inputRef.value?.resumeLiveListening()
  }
}

const loadHistory = async ({ reset = false } = {}) => {
  if (loadingHistory.value) return

  if (reset) {
    messages.value = []
    historyOffset.value = 0
    hasMoreHistory.value = true
    chatError.value = ''
  }

  if (!props.character?.friend_id) return
  if (!hasMoreHistory.value && !reset) return

  const shouldPreserveScroll = !reset && messages.value.length > 0
  if (shouldPreserveScroll) {
    chatHistoryRef.value?.captureScrollSnapshot()
  }

  loadingHistory.value = true

  try {
    const response = await api.get<{
      messages: Array<{ id: number; role: 'user' | 'assistant'; content: string; created_at: string }>
      next_offset: number
      has_more: boolean
    }>('/friend/message/history/', {
      params: {
        friend_id: props.character.friend_id,
        offset: historyOffset.value,
        limit: 20,
      },
    })

    const nextMessages = response.data.messages.map((message) => ({
      ...message,
      id: String(message.id),
    }))

    messages.value = reset ? nextMessages : [...nextMessages, ...messages.value]
    historyOffset.value = response.data.next_offset
    hasMoreHistory.value = response.data.has_more

    await nextTick()
    if (reset) {
      await chatHistoryRef.value?.scrollToBottom()
    } else if (shouldPreserveScroll) {
      await chatHistoryRef.value?.restoreScrollAfterPrepend()
    }
  } finally {
    loadingHistory.value = false
  }
}

watch(() => [props.character?.id, props.character?.friend_id] as const, async ([characterId, friendId]) => {
  if (!characterId || !friendId) {
    stopCurrentReply({ clearError: true })
    if (!characterId || !friendId) {
      messages.value = []
      historyOffset.value = 0
      hasMoreHistory.value = true
      chatError.value = ''
      inputResetToken.value += 1
    }
    return
  }

  stopCurrentReply({ clearError: true })
  inputResetToken.value += 1
  await loadHistory({ reset: true })
  inputRef.value?.focus()
}, { immediate: true })

onBeforeUnmount(() => {
  stopCurrentReply({ clearError: true })
})

const chatEnabled = computed(() => Boolean(props.character?.friend_id))
const inputPlaceholder = computed(() => {
  if (chatEnabled.value) return '输入一句话，按 Enter 发送。'
  if (!props.canManageFriend) return '登录后开始聊天。'
  return '正在准备聊天会话，请稍等。'
})
const inputDisabledReason = computed(() => {
  if (chatEnabled.value) return ''
  if (!props.canManageFriend) return '登录后才能开始文字和语音对话。'
  return '当前聊天会话还没准备好，请稍等或点击顶部按钮重新开始。'
})

const handleSend = async (message: string) => {
  if (!props.character?.friend_id) return
  stopCurrentReply({ clearError: true })

  const userMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'user',
    content: message,
    created_at: new Date().toISOString(),
  }
  const assistantMessage: ChatMessage = {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: '',
    created_at: new Date().toISOString(),
  }

  appendMessage(userMessage)
  appendMessage(assistantMessage)
  chatError.value = ''
  sendingMessage.value = true
  activeAssistantMessageId = assistantMessage.id
  activeStreamController = new AbortController()
  await chatHistoryRef.value?.scrollToBottom()

  let historyIncrement = 0

  try {
    await streamApi({
      url: '/friend/message/chat/',
      body: {
        friend_id: props.character.friend_id,
        message,
      },
      signal: activeStreamController.signal,
      onmessage(json, done) {
        if (json.meta?.history_increment) {
          historyIncrement = Number(json.meta.history_increment) || 0
          return
        }

        if (json.error) {
          const errorText = json.error || '聊天失败：未知错误'
          chatError.value = errorText
          messages.value = messages.value.map((item) => (
            item.id === assistantMessage.id
              ? { ...item, content: errorText }
              : item
          ))
          return
        }

        if (done) {
          historyOffset.value += historyIncrement
          const finalMessage = messages.value.find((item) => item.id === assistantMessage.id)
          if (finalMessage?.content) {
            void speakReply(finalMessage.content)
          }
          activeAssistantMessageId = null
          activeStreamController = null
          return
        }

        messages.value = messages.value.map((item) => (
          item.id === assistantMessage.id
            ? { ...item, content: item.content + (json.content || '') }
            : item
        ))
        void chatHistoryRef.value?.scrollToBottom()
      },
      onerror(error) {
        if (activeStreamController?.signal.aborted) {
          return
        }
        chatError.value = error instanceof Error ? error.message : '未知错误'
        messages.value = messages.value.map((item) => (
          item.id === assistantMessage.id
            ? { ...item, content: `聊天失败：${chatError.value}` }
            : item
        ))
        activeAssistantMessageId = null
        activeStreamController = null
      },
    })
  } finally {
    if (!activeStreamController?.signal.aborted) {
      sendingMessage.value = false
    }
  }
}
</script>

<template>
  <div
    class="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-visible rounded-[28px] border border-base-200 bg-base-100 shadow-sm"
  >
    <div class="border-b border-base-200 px-5 py-4 sm:px-6">
      <div class="flex items-center justify-between gap-4">
        <div>
          <div class="text-sm font-black text-base-content/80">对话</div>
          <div class="mt-1 text-xs text-base-content/50">
            {{ character?.friend_id ? '文字和语音都已就绪。' : '会话尚未建立。' }}
          </div>
        </div>
        <div class="rounded-full border border-base-200 bg-base-50 px-3 py-1 text-xs font-bold text-base-content/55">
          {{ sendingMessage ? '回复中' : (isReplySpeaking ? '语音播报中' : '在线') }}
        </div>
      </div>
    </div>

    <div class="flex min-h-0 flex-1 flex-col p-4 sm:p-5">
      <div class="mx-auto flex min-h-0 w-full max-w-[960px] flex-1 flex-col">
        <ChatHistory
          ref="chatHistoryRef"
          :messages="messages"
          :loading-history="loadingHistory"
          :has-more="hasMoreHistory"
          @load-more="loadHistory"
        />

        <div v-if="chatError" class="mt-3 rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">
          {{ chatError }}
        </div>

        <div class="relative z-20 mt-4">
          <InputField
            ref="inputRef"
            :autofocus="true"
            :disabled="!chatEnabled"
            :disabled-reason="inputDisabledReason"
            :pending="sendingMessage || isReplySpeaking || pending"
            :placeholder="inputPlaceholder"
            :reset-token="inputResetToken"
            @send="handleSend"
            @stop="stopCurrentReply"
          />
        </div>
      </div>
    </div>
  </div>
</template>

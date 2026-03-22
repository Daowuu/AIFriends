<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import api from '@/api/http'
import streamApi from '@/api/streamApi'
import AppIcon from '@/components/AppIcon.vue'
import CharacterForm from '@/components/CharacterForm.vue'
import MarkdownContent from '@/components/MarkdownContent.vue'
import ApiSettingsView from '@/views/ApiSettingsView.vue'
import type { Character, CharacterFormPayload, VoiceOption } from '@/types/character'
import type { StudioChatDebug, StudioOverview, StudioRecentDebugSummary } from '@/types/studio'
import { useCharacterChatNavigation } from '@/utils/useCharacterChatNavigation'

type CharacterFormStudioExpose = {
  previewVoiceFromCurrentDraft: (text?: string) => Promise<void>
  stopVoicePreview: () => void
}

const studioTab = ref<'workflow' | 'settings'>('workflow')
const workspacePanel = ref<'configure' | 'diagnostics'>('configure')
const loading = ref(true)
const pending = ref(false)
const overviewError = ref('')
const characters = ref<Character[]>([])
const voices = ref<VoiceOption[]>([])
const runtimeSummary = ref<StudioOverview['runtime_summary'] | null>(null)
const recentDebugSummary = ref<StudioRecentDebugSummary | null>(null)
const selectedCharacterId = ref<number | null>(null)
const hasDraftSlot = ref(false)
const draftSlotVersion = ref(0)
const searchQuery = ref('')
const testPrompt = ref('用你的角色语气做一个简短自我介绍。')
const testReply = ref('')
const testPending = ref(false)
const testError = ref('')
const testDebug = ref<StudioChatDebug | null>(null)
const memoryActionPending = ref(false)
const memoryActionMessage = ref('')
const memoryActionError = ref('')
const voiceSampleText = ref('你好呀，我是这个角色的语音试听。')
const studioVoicePreviewPending = ref(false)
const studioVoicePreviewError = ref('')
const studioVoicePreviewing = ref(false)
const characterFormRef = ref<CharacterFormStudioExpose | null>(null)

const { openCharacterChat } = useCharacterChatNavigation()

const currentCharacter = computed(() => (
  selectedCharacterId.value
    ? characters.value.find((character) => character.id === selectedCharacterId.value) ?? null
    : null
))

const editorMode = computed<'create' | 'update'>(() => (currentCharacter.value ? 'update' : 'create'))
const formKey = computed(() => (
  currentCharacter.value ? `character-${currentCharacter.value.id}` : `draft-${draftSlotVersion.value}`
))

const filteredCharacters = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return characters.value
  return characters.value.filter((character) => (
    character.name.toLowerCase().includes(query)
    || character.profile.toLowerCase().includes(query)
    || character.ai_config.reply_style.toLowerCase().includes(query)
  ))
})

const selectedCharacterRuntimeSummary = computed(() => {
  if (!currentCharacter.value) return null
  return {
    voice: currentCharacter.value.voice?.name || '未配置音色',
    memoryMode: currentCharacter.value.ai_config.memory_mode,
    replyStyle: currentCharacter.value.ai_config.reply_style,
    initiative: currentCharacter.value.ai_config.initiative_level,
    canChat: Boolean(currentCharacter.value.friend_id),
  }
})

const characterCount = computed(() => characters.value.length)
const customVoiceCount = computed(() => voices.value.filter((voice) => voice.source === 'custom').length)
const readyCharacterCount = computed(() => characters.value.filter((character) => Boolean(character.voice_id)).length)
const runtimeStatusTone = computed(() => {
  const status = runtimeSummary.value?.chat_runtime_status
  if (status === 'invalid') return 'text-amber-200 bg-amber-400/15 border-amber-300/25'
  if (status === 'missing') return 'text-sky-100 bg-sky-400/15 border-sky-300/25'
  return 'text-emerald-100 bg-emerald-400/15 border-emerald-300/25'
})
const runtimeStatusLabel = computed(() => {
  const status = runtimeSummary.value?.chat_runtime_status
  if (status === 'invalid') return '配置待修复'
  if (status === 'missing') return '等待接入模型'
  return '运行中'
})

const testDebugDisplay = computed(() => {
  const debug = testDebug.value
  if (!debug) return null

  return {
    promptLayers: debug.prompt_layers.join(' / '),
    memoryMode: debug.memory_injection.mode,
    usedSummary: debug.memory_injection.used_summary,
    usedRelationshipMemory: debug.memory_injection.used_relationship_memory,
    usedPreferenceMemory: debug.memory_injection.used_user_preference_memory,
    memoryUpdateReason: debug.memory_update.reason,
    cooldownActive: debug.memory_update.cooldown_active ?? false,
    runtimeSource: debug.runtime_source,
    fallbackUsed: debug.fallback_used,
    errorTag: debug.error_tag || '',
  }
})

const getDebugMemoryFlags = (debug: StudioChatDebug | null) => ({
  hasSummary: debug?.memory_injection.used_summary ?? false,
  hasRelationshipMemory: debug?.memory_injection.used_relationship_memory ?? false,
  hasPreferenceMemory: debug?.memory_injection.used_user_preference_memory ?? false,
})

const diagnosticSummary = computed(() => {
  const summary = runtimeSummary.value
  if (!summary) return null

  if (summary.chat_runtime_status === 'invalid') {
    const actionMap: Record<string, string> = {
      user_missing_api_key: '到右侧“模型与语音配置”里补全聊天 API Key，然后重新试聊。',
      user_missing_api_base: '到右侧“模型与语音配置”里补全聊天 API Base，或切回服务端默认。',
      user_missing_model_name: '到右侧“模型与语音配置”里补全聊天模型名，或关闭个人聊天配置。',
    }
    return {
      level: 'warning',
      title: '个人聊天配置不完整',
      detail: summary.chat_runtime_reason || '当前个人聊天配置不可用。',
      action: actionMap[summary.chat_runtime_reason] || '检查聊天配置后重新试聊。',
    }
  }

  if (summary.chat_runtime_status === 'missing') {
    return {
      level: 'info',
      title: '当前没有可用的聊天模型配置',
      detail: '系统会退回本地保底回复，适合调 UI，不适合做正式角色试聊。',
      action: '去“模型与语音配置”补一套聊天模型配置，再回来试聊。',
    }
  }

  return {
      level: 'success',
      title: '聊天运行态正常',
      detail: `当前会优先使用 ${summary.chat_runtime.label}。`,
      action: summary.dashscope_audio_reuse_source
        ? `当前网关：${summary.chat_runtime.api_base || '未显式设置'}；语音链路复用来源：${summary.dashscope_audio_reuse_source}`
        : (summary.chat_runtime.api_base
          ? `当前网关：${summary.chat_runtime.api_base}`
          : '可以直接开始试聊或进入正式聊天。'),
  }
})

const loadStudioOverview = async (preferredCharacterId?: number | null) => {
  loading.value = true
  overviewError.value = ''

  try {
    const response = await api.get<StudioOverview>('/studio/overview/')
    characters.value = response.data.characters
    voices.value = response.data.voices
    runtimeSummary.value = response.data.runtime_summary
    recentDebugSummary.value = response.data.recent_debug_summary

    const nextSelectedId = preferredCharacterId ?? selectedCharacterId.value
    if (nextSelectedId && response.data.characters.some((character) => character.id === nextSelectedId)) {
      selectedCharacterId.value = nextSelectedId
    } else if (response.data.characters.length > 0) {
      const firstCharacter = response.data.characters[0]
      selectedCharacterId.value = firstCharacter ? firstCharacter.id : null
    } else {
      selectedCharacterId.value = null
    }
  } catch (error: unknown) {
    overviewError.value = 'AI Studio 加载失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      overviewError.value = response?.data?.detail || overviewError.value
    }
  } finally {
    loading.value = false
  }
}

const buildCharacterFormData = (payload: CharacterFormPayload) => {
  const formData = new FormData()
  formData.append('name', payload.name)
  formData.append('profile', payload.profile)
  formData.append('custom_prompt', payload.customPrompt)
  formData.append('voice_id', payload.voiceId ? String(payload.voiceId) : '')
  formData.append('custom_voice_name', payload.customVoiceName)
  formData.append('custom_voice_code', payload.customVoiceCode)
  formData.append('custom_voice_model_name', payload.customVoiceModelName)
  formData.append('custom_voice_description', payload.customVoiceDescription)
  formData.append('reply_style', payload.aiConfig.reply_style)
  formData.append('reply_length', payload.aiConfig.reply_length)
  formData.append('initiative_level', payload.aiConfig.initiative_level)
  formData.append('memory_mode', payload.aiConfig.memory_mode)
  formData.append('persona_boundary', payload.aiConfig.persona_boundary)
  formData.append('tools_enabled', String(payload.aiConfig.tools_enabled))
  formData.append('tools_require_confirmation', String(payload.aiConfig.tools_require_confirmation))
  formData.append('tools_read_only', String(payload.aiConfig.tools_read_only))
  if (payload.photoFile) formData.append('photo', payload.photoFile)
  if (payload.backgroundImageFile) formData.append('background_image', payload.backgroundImageFile)
  if (payload.removePhoto) formData.append('remove_photo', 'true')
  if (payload.removeBackgroundImage) formData.append('remove_background_image', 'true')
  return formData
}

const handleSubmit = async (payload: CharacterFormPayload) => {
  pending.value = true
  overviewError.value = ''

  try {
    const formData = buildCharacterFormData(payload)
    if (editorMode.value === 'create') {
      const response = await api.post<{ character: Character }>('/create/character/create/', formData)
      hasDraftSlot.value = false
      await loadStudioOverview(response.data.character.id)
    } else if (currentCharacter.value) {
      const response = await api.post<{ character: Character }>(
        `/create/character/${currentCharacter.value.id}/update/`,
        formData,
      )
      await loadStudioOverview(response.data.character.id)
    }
  } catch (error: unknown) {
    overviewError.value = editorMode.value === 'create' ? '创建角色失败。' : '保存角色失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      overviewError.value = response?.data?.detail || overviewError.value
    }
  } finally {
    pending.value = false
  }
}

const removeCharacter = async (character: Character) => {
  await api.post(`/create/character/${character.id}/remove/`)
  await loadStudioOverview(character.id === selectedCharacterId.value ? null : selectedCharacterId.value)
}

const startCreateMode = () => {
  hasDraftSlot.value = true
  draftSlotVersion.value += 1
  selectedCharacterId.value = null
  workspacePanel.value = 'configure'
  testReply.value = ''
  testError.value = ''
  testDebug.value = null
}

const selectCharacter = (character: Character) => {
  selectedCharacterId.value = character.id
  workspacePanel.value = 'configure'
  testReply.value = ''
  testError.value = ''
  testDebug.value = null
}

const syncCharacter = (nextCharacter: Character) => {
  characters.value = characters.value.map((item) => (
    item.id === nextCharacter.id ? nextCharacter : item
  ))
  if (selectedCharacterId.value === nextCharacter.id) {
    selectedCharacterId.value = nextCharacter.id
  }
}

const ensureFriendSession = async (character: Character) => {
  if (character.friend_id) return character

  const response = await api.post<{ friend: { id: number } }>('/friend/get_or_create/', {
    character_id: character.id,
  })

  const nextCharacter = {
    ...character,
    friend_id: response.data.friend.id,
  }
  syncCharacter(nextCharacter)
  return nextCharacter
}

const runTrialChat = async () => {
  if (!currentCharacter.value) {
    testError.value = '请先选择一个角色。'
    return
  }

  if (!currentCharacter.value.id) {
    testError.value = '请先保存角色，再试聊。'
    return
  }

  const prompt = testPrompt.value.trim()
  if (!prompt) {
    testError.value = '请输入一段试聊文本。'
    return
  }

  testPending.value = true
  testReply.value = ''
  testError.value = ''
  testDebug.value = null

  try {
    const character = await ensureFriendSession(currentCharacter.value)
    let debugResult: StudioChatDebug | null = null

    await streamApi({
      url: '/friend/message/chat/',
      body: {
        friend_id: character.friend_id,
        message: prompt,
      },
      onmessage(json, done) {
        if (json.error) {
          testError.value = json.error
          return
        }
        if (json.content) {
          testReply.value += json.content
        }
        if (json.meta?.debug) {
          debugResult = json.meta.debug as StudioChatDebug
          testDebug.value = debugResult
        }
        if (done) {
          testPending.value = false
        }
      },
      onerror(error) {
        testPending.value = false
        testError.value = error instanceof Error ? error.message : '试聊失败。'
      },
    })

    const latestDebug = debugResult as StudioChatDebug | null
    const memoryFlags = getDebugMemoryFlags(latestDebug)
    recentDebugSummary.value = {
      friend_id: character.friend_id || 0,
      character_id: character.id,
      character_name: character.name,
      memory_mode: character.ai_config.memory_mode,
      voice_name: character.voice?.name || '',
      last_message_at: new Date().toISOString(),
      memory_updated_at: '',
      last_debug_at: new Date().toISOString(),
      has_summary: memoryFlags.hasSummary,
      has_preference_memory: memoryFlags.hasPreferenceMemory,
      prompt_layers: latestDebug?.prompt_layers || [],
      runtime_source: latestDebug?.runtime_source || '',
      fallback_used: latestDebug?.fallback_used ?? false,
      error_tag: latestDebug?.error_tag || '',
      memory_update_reason: latestDebug?.memory_update.reason || '',
      memory_update_triggered: latestDebug?.memory_update.triggered ?? false,
      used_summary: memoryFlags.hasSummary,
      used_relationship_memory: memoryFlags.hasRelationshipMemory,
      used_user_preference_memory: memoryFlags.hasPreferenceMemory,
    }
    await loadStudioOverview(character.id)
  } catch (error: unknown) {
    testError.value = error instanceof Error ? error.message : '试聊失败。'
    testPending.value = false
  } finally {
    if (!testPending.value) return
    testPending.value = false
  }
}

const handleStudioMemoryReset = async () => {
  if (!currentCharacter.value?.friend_id || memoryActionPending.value) return

  if (typeof window !== 'undefined' && !window.confirm('清空长期记忆会移除这段会话的摘要、关系记忆和用户偏好记忆。是否继续？')) {
    return
  }

  memoryActionPending.value = true
  memoryActionMessage.value = ''
  memoryActionError.value = ''

  try {
    const response = await api.post<{ detail: string }>('/friend/message/reset/', {
      friend_id: currentCharacter.value.friend_id,
      mode: 'full',
    })
    memoryActionMessage.value = response.data.detail
    testReply.value = ''
    testDebug.value = null
    await loadStudioOverview(currentCharacter.value.id)
  } catch (error: unknown) {
    memoryActionError.value = '清空长期记忆失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      memoryActionError.value = response?.data?.detail || memoryActionError.value
    }
  } finally {
    memoryActionPending.value = false
  }
}

const handleStudioVoicePreview = async () => {
  if (!characterFormRef.value) return

  studioVoicePreviewPending.value = true
  studioVoicePreviewError.value = ''

  try {
    await characterFormRef.value.previewVoiceFromCurrentDraft(voiceSampleText.value)
  } finally {
    studioVoicePreviewPending.value = false
  }
}

onMounted(() => {
  void loadStudioOverview()
})
</script>

<template>
  <section class="relative overflow-hidden">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(234,179,8,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(20,184,166,0.16),_transparent_26%),linear-gradient(180deg,#fcfbf7_0%,#f7f3ea_55%,#f6f4ee_100%)]" />
    <div class="pointer-events-none absolute inset-x-0 top-0 h-[320px] bg-[linear-gradient(135deg,rgba(15,23,42,0.10),transparent_55%)]" />

    <div class="relative mx-auto max-w-[1700px] p-4 sm:p-6">
      <div class="overflow-hidden rounded-[40px] border border-[#17342d]/10 bg-[#10231d] text-[#f7f1e5] shadow-[0_28px_90px_rgba(16,35,29,0.28)]">
        <div class="grid gap-10 px-6 py-7 sm:px-8 xl:grid-cols-[minmax(0,1fr)_420px]">
          <div>
            <div class="inline-flex items-center gap-3 rounded-full border border-white/12 bg-white/6 px-4 py-2 text-[11px] font-black uppercase tracking-[0.32em] text-[#f3d7a3]">
              <AppIcon name="spark" icon-class="h-4 w-4" />
              AI Studio
            </div>
            <h1 class="mt-5 max-w-4xl text-4xl font-black tracking-tight text-white sm:text-5xl">
              把角色定义、模型配置、试听试聊和运行态诊断放进同一条工作流
            </h1>
            <p class="mt-4 max-w-3xl text-sm leading-8 text-white/72 sm:text-[15px]">
              这里不是普通后台，而是面向 AI 创作者的工作台。先把角色打磨好，再直接验证语音、记忆和聊天运行态，最后进入正式会话。
            </p>

            <div class="mt-8 flex flex-wrap gap-3">
              <button
                type="button"
                class="inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-bold transition"
                :class="studioTab === 'workflow'
                  ? 'bg-[#f2dfbd] text-[#16231f] shadow-[0_8px_24px_rgba(242,223,189,0.26)]'
                  : 'border border-white/12 bg-white/6 text-white/78 hover:bg-white/10'"
                @click="studioTab = 'workflow'"
              >
                <AppIcon name="create" icon-class="h-4 w-4" />
                角色工作流
              </button>
              <button
                type="button"
                class="inline-flex items-center gap-2 rounded-full px-5 py-3 text-sm font-bold transition"
                :class="studioTab === 'settings'
                  ? 'bg-[#f2dfbd] text-[#16231f] shadow-[0_8px_24px_rgba(242,223,189,0.26)]'
                  : 'border border-white/12 bg-white/6 text-white/78 hover:bg-white/10'"
                @click="studioTab = 'settings'"
              >
                <AppIcon name="settings" icon-class="h-4 w-4" />
                模型与语音配置
              </button>
            </div>
          </div>

          <div class="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
            <div class="rounded-[28px] border border-white/10 bg-white/6 p-5 backdrop-blur-sm">
              <div class="text-xs font-black uppercase tracking-[0.2em] text-white/45">角色库</div>
              <div class="mt-3 text-3xl font-black text-white">{{ characterCount }}</div>
              <div class="mt-1 text-sm text-white/62">已创建角色</div>
            </div>
            <div class="rounded-[28px] border border-white/10 bg-white/6 p-5 backdrop-blur-sm">
              <div class="text-xs font-black uppercase tracking-[0.2em] text-white/45">音色</div>
              <div class="mt-3 text-3xl font-black text-white">{{ customVoiceCount }}</div>
              <div class="mt-1 text-sm text-white/62">自定义音色</div>
            </div>
            <div class="rounded-[28px] border border-white/10 bg-white/6 p-5 backdrop-blur-sm">
              <div class="text-xs font-black uppercase tracking-[0.2em] text-white/45">运行态</div>
              <div class="mt-3">
                <span class="inline-flex rounded-full border px-3 py-1 text-sm font-bold" :class="runtimeStatusTone">
                  {{ runtimeStatusLabel }}
                </span>
              </div>
              <div class="mt-3 text-sm text-white/62">{{ readyCharacterCount }} 个角色已挂上音色</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="studioTab === 'settings'" class="mt-8">
        <ApiSettingsView embedded />
      </div>

      <div v-else class="mt-8">
        <div v-if="overviewError" class="alert alert-error mb-6">{{ overviewError }}</div>

        <div
          v-if="loading"
          class="grid min-h-[560px] place-items-center rounded-[36px] border border-[#d9d1bf] bg-white/80 text-base-content/55 shadow-[0_20px_60px_rgba(15,23,42,0.06)] backdrop-blur"
        >
          正在加载 AI Studio...
        </div>

        <div v-else class="space-y-6">
          <section class="overflow-hidden rounded-[34px] border border-[#d8d1c5] bg-[linear-gradient(180deg,rgba(255,251,243,0.98),rgba(249,244,232,0.95))] p-5 shadow-[0_16px_48px_rgba(15,23,42,0.06)]">
            <div class="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <div class="text-xs font-black uppercase tracking-[0.22em] text-[#7b6a4b]">Character Library</div>
                <h2 class="mt-2 text-2xl font-black text-[#16231f]">角色库</h2>
                <p class="mt-2 text-sm leading-7 text-[#495650]">把角色库提到同一行里，切角色时不再挤压主工作区。</p>
              </div>

              <div class="flex flex-col gap-3 xl:min-w-[520px] xl:items-end">
                <div class="flex w-full flex-col gap-3 sm:flex-row xl:justify-end">
                  <label class="flex min-w-0 flex-1 items-center gap-3 rounded-full border border-[#d7cdb9] bg-white px-4 py-3 shadow-sm">
                    <AppIcon name="search" icon-class="h-4 w-4 text-[#7c6d55]" />
                    <input v-model="searchQuery" type="text" class="w-full bg-transparent text-sm outline-none" placeholder="筛选角色、风格、设定" />
                  </label>
                  <button
                    type="button"
                    class="inline-flex items-center justify-center gap-2 rounded-full bg-[#16231f] px-4 py-2.5 text-sm font-bold text-[#f7f1e5] transition hover:bg-[#1e342d]"
                    @click="startCreateMode"
                  >
                    <AppIcon name="create" icon-class="h-4 w-4" />
                    新角色
                  </button>
                </div>

                <div class="flex flex-wrap gap-2 text-xs font-bold">
                  <span class="rounded-full bg-[#efe4cf] px-3 py-1 text-[#6f5832]">角色 {{ characterCount }}</span>
                  <span class="rounded-full bg-[#e2efe8] px-3 py-1 text-[#2f6b55]">有音色 {{ readyCharacterCount }}</span>
                  <span class="rounded-full bg-[#f4e5da] px-3 py-1 text-[#8b5a37]">自定义音色 {{ customVoiceCount }}</span>
                </div>
              </div>
            </div>

            <div
              v-if="characters.length === 0"
              class="mt-5 rounded-[30px] border border-dashed border-[#d1c7b4] bg-white/75 p-7 text-sm leading-7 text-[#5d665f] shadow-sm"
            >
              还没有角色。先创建一个角色，再开始做 AI 配置、试听和试聊。
            </div>

            <div v-else class="mt-5 overflow-x-auto pb-2">
              <div class="flex min-w-max gap-3">
                <button
                  v-if="hasDraftSlot"
                  type="button"
                  class="group flex min-w-[220px] items-center gap-3 rounded-[24px] border px-4 py-3 text-left transition"
                  :class="selectedCharacterId === null
                    ? 'border-[#16231f] bg-[#16231f] text-[#f7f1e5] shadow-[0_14px_32px_rgba(22,35,31,0.18)]'
                    : 'border-dashed border-[#cdbfa7] bg-[#fff8eb] text-[#26322e] hover:border-[#bda984] hover:bg-[#fff3dd]'"
                  @click="startCreateMode"
                >
                  <div class="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#efe4cf] text-[#6f5832]">
                    <AppIcon name="create" icon-class="h-5 w-5" />
                  </div>

                  <div class="min-w-0 flex-1">
                    <div class="truncate text-sm font-black">新角色草稿</div>
                    <div
                      class="mt-1 truncate text-xs"
                      :class="selectedCharacterId === null ? 'text-[#f7f1e5]/70' : 'text-[#6e776f]'"
                    >
                      先写设定，再保存成正式角色
                    </div>
                  </div>

                  <div
                    class="rounded-full px-2.5 py-1 text-[11px] font-bold"
                    :class="selectedCharacterId === null
                      ? 'bg-white/10 text-[#f7f1e5]'
                      : 'bg-[#f3ead9] text-[#7b6a4b]'"
                  >
                    草稿
                  </div>
                </button>

                <button
                  v-for="character in filteredCharacters"
                  :key="character.id"
                  type="button"
                  class="group flex min-w-[220px] items-center gap-3 rounded-[24px] border px-4 py-3 text-left transition"
                  :class="selectedCharacterId === character.id
                    ? 'border-[#16231f] bg-[#16231f] text-[#f7f1e5] shadow-[0_14px_32px_rgba(22,35,31,0.18)]'
                    : 'border-[#d7cdb9] bg-white/82 text-[#26322e] hover:border-[#c8bda8] hover:bg-[#fffaf0]'"
                  @click="selectCharacter(character)"
                >
                  <div class="h-12 w-12 shrink-0 overflow-hidden rounded-2xl bg-[#efe4cf]">
                    <img
                      v-if="character.photo"
                      :src="character.photo"
                      :alt="character.name"
                      class="h-full w-full object-cover"
                    >
                    <div v-else class="grid h-full w-full place-items-center text-sm font-black">
                      {{ character.name.slice(0, 1) }}
                    </div>
                  </div>

                  <div class="min-w-0 flex-1">
                    <div class="truncate text-sm font-black">{{ character.name }}</div>
                    <div
                      class="mt-1 truncate text-xs"
                      :class="selectedCharacterId === character.id ? 'text-[#f7f1e5]/70' : 'text-[#6e776f]'"
                    >
                      {{ character.voice?.name || '未配音色' }} · {{ character.ai_config.memory_mode }}
                    </div>
                  </div>

                  <div
                    class="rounded-full px-2.5 py-1 text-[11px] font-bold"
                    :class="selectedCharacterId === character.id
                      ? 'bg-white/10 text-[#f7f1e5]'
                      : 'bg-[#f3ead9] text-[#7b6a4b]'"
                  >
                    {{ character.friend_id ? '已试聊' : '待试聊' }}
                  </div>
                </button>
              </div>
            </div>
          </section>

          <div class="space-y-5">
            <div class="overflow-hidden rounded-[34px] border border-[#d8d1c5] bg-white/92 shadow-[0_20px_64px_rgba(15,23,42,0.06)]">
              <div class="flex flex-wrap items-center justify-between gap-4 border-b border-[#ebe4d8] bg-[linear-gradient(135deg,rgba(255,248,236,0.95),rgba(246,250,247,0.92))] px-6 py-5">
                <div>
                  <div class="text-xs font-black uppercase tracking-[0.22em] text-[#7b6a4b]">
                    {{ currentCharacter ? '编辑角色' : '创建角色' }}
                  </div>
                  <div class="mt-2 text-2xl font-black text-[#16231f]">
                    {{ currentCharacter ? currentCharacter.name : '新角色草稿' }}
                  </div>
                  <div class="mt-2 text-sm text-[#55635c]">
                    {{ currentCharacter ? '调整角色设定、AI 规则和音色，然后在右侧马上试听试聊。' : '先把基础人设写清楚，再逐步补 AI 和语音能力。' }}
                  </div>
                </div>

                <div class="flex flex-wrap gap-3">
                  <button
                    type="button"
                    class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-bold transition"
                    :class="workspacePanel === 'configure'
                      ? 'bg-[#16231f] text-[#f7f1e5]'
                      : 'border border-[#d4c7ae] bg-white text-[#26322e] hover:bg-[#fff7e9]'"
                    @click="workspacePanel = 'configure'"
                  >
                    角色配置
                  </button>
                  <button
                    type="button"
                    class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-bold transition"
                    :class="workspacePanel === 'diagnostics'
                      ? 'bg-[#16231f] text-[#f7f1e5]'
                      : 'border border-[#d4c7ae] bg-white text-[#26322e] hover:bg-[#fff7e9]'"
                    @click="workspacePanel = 'diagnostics'"
                  >
                    试聊诊断
                  </button>
                  <button
                    v-if="currentCharacter"
                    type="button"
                    class="inline-flex items-center gap-2 rounded-full border border-[#d4c7ae] bg-white px-4 py-2.5 text-sm font-bold text-[#26322e] transition hover:bg-[#fff7e9]"
                    @click="openCharacterChat(currentCharacter)"
                  >
                    正式聊天
                  </button>
                  <button
                    v-if="currentCharacter"
                    type="button"
                    class="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-bold text-[#9c3e2f] transition hover:bg-[#fff0ed]"
                    @click="removeCharacter(currentCharacter)"
                  >
                    删除角色
                  </button>
                </div>
              </div>

              <div v-show="workspacePanel === 'configure'" class="px-5 py-5 sm:px-6">
                <CharacterForm
                  ref="characterFormRef"
                  :key="formKey"
                  :mode="editorMode"
                  :initial-character="currentCharacter"
                  :voices="voices"
                  :pending="pending"
                  :show-voice-preview="false"
                  @submit="handleSubmit"
                  @voices-changed="void loadStudioOverview(currentCharacter?.id ?? null)"
                  @voice-preview-state-changed="({ isPreviewing, error }) => {
                    studioVoicePreviewing = isPreviewing
                    studioVoicePreviewError = error
                  }"
                />
              </div>
              <div v-show="workspacePanel === 'diagnostics'" class="grid gap-5 px-5 py-5 sm:px-6 xl:grid-cols-[minmax(0,1.12fr)_360px]">
                <div class="overflow-hidden rounded-[34px] border border-[#d8d1c5] bg-white/92 p-5 shadow-[0_16px_56px_rgba(15,23,42,0.06)]">
                  <div class="text-xs font-black uppercase tracking-[0.22em] text-[#7b6a4b]">Test Panel</div>
                  <h2 class="mt-2 text-2xl font-black text-[#16231f]">试聊与诊断</h2>
                  <p class="mt-2 text-sm leading-7 text-[#5b665f]">
                    这里单独做试聊，不再和角色配置挤在一屏里。先调角色，再回来验证回复、记忆和运行态。
                  </p>

                  <textarea
                    v-model="testPrompt"
                    class="mt-5 min-h-36 w-full rounded-[24px] border border-[#e7e0d4] bg-[#fcfbf7] px-4 py-4 text-sm leading-7 text-[#16231f] placeholder:text-[#9a8f7d] outline-none transition focus:border-[#d9cbb3] focus:bg-white"
                    placeholder="输入一段试聊文本。"
                  />

                  <div class="mt-4 flex flex-wrap gap-3">
                    <button
                      type="button"
                      class="inline-flex items-center gap-2 rounded-full bg-[#16231f] px-5 py-3 text-sm font-bold text-[#f7f1e5] transition hover:bg-[#1e342d] disabled:cursor-not-allowed disabled:opacity-50"
                      :disabled="testPending || !currentCharacter"
                      @click="runTrialChat"
                    >
                      {{ testPending ? '试聊中...' : '开始试聊' }}
                    </button>
                    <button
                      type="button"
                      class="inline-flex items-center gap-2 rounded-full border border-[#d4c7ae] bg-white px-5 py-3 text-sm font-bold text-[#26322e] transition hover:bg-[#fff7e9]"
                      @click="studioTab = 'settings'"
                    >
                      模型配置
                    </button>
                  </div>

                  <div class="mt-5 rounded-[22px] border border-[#e7e0d4] bg-[#fcfbf7] p-4">
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7c6d55]">语音试听</div>
                    <p class="mt-2 text-xs leading-6 text-[#7b857f]">
                      这里会直接使用右侧当前草稿的音色配置，不需要先保存角色。
                    </p>
                    <textarea
                      v-model="voiceSampleText"
                      class="mt-4 min-h-24 w-full rounded-[20px] border border-[#e7e0d4] bg-white px-4 py-3 text-sm leading-7 text-[#16231f] placeholder:text-[#9a8f7d] outline-none transition focus:border-[#d9cbb3]"
                      maxlength="300"
                      placeholder="输入一段试听文案。"
                    />
                    <div class="mt-4 flex flex-wrap gap-3">
                      <button
                        type="button"
                        class="inline-flex items-center gap-2 rounded-full border border-[#d4c7ae] bg-white px-5 py-3 text-sm font-bold text-[#26322e] transition hover:bg-[#fff7e9] disabled:cursor-not-allowed disabled:opacity-50"
                        :disabled="studioVoicePreviewPending || !characterFormRef"
                        @click="handleStudioVoicePreview"
                      >
                        {{ studioVoicePreviewing ? '停止试听' : (studioVoicePreviewPending ? '处理中...' : '试听音色') }}
                      </button>
                    </div>
                    <div v-if="studioVoicePreviewError" class="mt-4 rounded-[18px] border border-[#e9b9ac] bg-[#fff0ed] px-4 py-3 text-sm text-[#9c3e2f]">
                      {{ studioVoicePreviewError }}
                    </div>
                  </div>

                  <div v-if="testError" class="mt-4 rounded-[22px] border border-[#e9b9ac] bg-[#fff0ed] px-4 py-3 text-sm text-[#9c3e2f]">
                    {{ testError }}
                  </div>

                  <div class="mt-5 rounded-[22px] border border-[#e7e0d4] bg-[#fcfbf7] p-4">
                    <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7c6d55]">试聊回复</div>
                    <div v-if="testReply" class="mt-3 min-h-44 text-sm leading-7 text-[#46534d]">
                      <MarkdownContent :content="testReply" />
                    </div>
                    <div v-else class="mt-3 min-h-44 text-sm leading-7 text-[#7b857f]">
                      这里会显示一轮试聊的回复内容。
                    </div>
                  </div>
                </div>

                <div class="space-y-5">
                  <div class="rounded-[34px] border border-[#d8d1c5] bg-white/92 p-5 shadow-[0_16px_56px_rgba(15,23,42,0.06)]">
                    <div class="text-xs font-black uppercase tracking-[0.22em] text-[#7b6a4b]">Runtime</div>
                    <h2 class="mt-2 text-2xl font-black text-[#16231f]">运行态摘要</h2>

                    <div
                      v-if="diagnosticSummary"
                      class="mt-4 rounded-[24px] border p-4 text-sm"
                      :class="{
                        'border-emerald-200 bg-emerald-50/70 text-emerald-950': diagnosticSummary.level === 'success',
                        'border-amber-200 bg-amber-50/80 text-amber-950': diagnosticSummary.level === 'warning',
                        'border-sky-200 bg-sky-50/80 text-sky-950': diagnosticSummary.level === 'info',
                      }"
                    >
                      <div class="font-bold">{{ diagnosticSummary.title }}</div>
                      <div class="mt-2 leading-7">{{ diagnosticSummary.detail }}</div>
                      <div class="mt-2 text-xs leading-6 opacity-80">{{ diagnosticSummary.action }}</div>
                    </div>

                    <div class="mt-4 space-y-3 text-sm">
                      <div class="rounded-[22px] border border-[#e7e0d4] bg-[#fcfbf7] p-4">
                        <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7c6d55]">聊天</div>
                        <div class="mt-2 font-semibold text-[#16231f]">{{ runtimeSummary?.chat_runtime.label || '未启用' }}</div>
                        <div class="mt-1 break-all text-[#5b665f]">{{ runtimeSummary?.chat_runtime.model_name || '未设置模型' }}</div>
                      </div>
                      <div class="rounded-[22px] border border-[#e7e0d4] bg-[#fcfbf7] p-4">
                        <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7c6d55]">ASR / TTS</div>
                        <div class="mt-2 text-[#46534d]">ASR：{{ runtimeSummary?.asr_runtime.label || '未启用' }}</div>
                        <div class="mt-1 text-[#46534d]">TTS：{{ runtimeSummary?.tts_runtime.label || '未启用' }}</div>
                      </div>
                      <div
                        v-if="selectedCharacterRuntimeSummary"
                        class="rounded-[22px] border border-[#e7e0d4] bg-[#fcfbf7] p-4"
                      >
                        <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7c6d55]">当前角色摘要</div>
                        <div class="mt-2 text-[#46534d]">风格：{{ selectedCharacterRuntimeSummary.replyStyle }}</div>
                        <div class="mt-1 text-[#46534d]">记忆：{{ selectedCharacterRuntimeSummary.memoryMode }}</div>
                        <div class="mt-1 text-[#46534d]">主动性：{{ selectedCharacterRuntimeSummary.initiative }}</div>
                        <div class="mt-1 text-[#46534d]">音色：{{ selectedCharacterRuntimeSummary.voice }}</div>
                      </div>
                    </div>
                  </div>

                  <div class="rounded-[34px] border border-[#d8d1c5] bg-white/92 p-5 shadow-[0_16px_56px_rgba(15,23,42,0.06)]">
                    <div class="flex items-start justify-between gap-3">
                      <div>
                        <div class="text-xs font-black uppercase tracking-[0.22em] text-[#7b6a4b]">Diagnostics</div>
                        <h2 class="mt-2 text-2xl font-black text-[#16231f]">调试信息</h2>
                      </div>
                      <button
                        type="button"
                        class="rounded-full border border-[#d9cbb3] px-4 py-2 text-xs font-bold text-[#8a5a34] transition hover:bg-[#fff2e2] disabled:cursor-not-allowed disabled:opacity-50"
                        :disabled="!currentCharacter?.friend_id || memoryActionPending"
                        @click="handleStudioMemoryReset"
                      >
                        {{ memoryActionPending ? '处理中...' : '清空长期记忆' }}
                      </button>
                    </div>

                    <div class="mt-3 text-xs leading-6 text-[#7b857f]">
                      这里只清当前创作者和这个角色之间的会话记忆，不改角色本体设定。
                    </div>

                    <div v-if="memoryActionMessage" class="alert alert-success mt-4 text-sm">
                      {{ memoryActionMessage }}
                    </div>
                    <div v-if="memoryActionError" class="alert alert-error mt-4 text-sm">
                      {{ memoryActionError }}
                    </div>

                    <div class="mt-4 rounded-[22px] border border-[#e7e0d4] bg-[#fcfbf7] p-4 text-sm">
                      <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7c6d55]">本轮试聊</div>
                      <div v-if="testDebugDisplay" class="mt-3 space-y-2 text-[#4d5953]">
                        <div>Prompt Layers：{{ testDebugDisplay.promptLayers }}</div>
                        <div>
                          记忆注入：{{ testDebugDisplay.memoryMode }}
                          <span class="text-[#7b857f]">
                            （摘要 {{ testDebugDisplay.usedSummary ? '开' : '关' }} / 关系 {{ testDebugDisplay.usedRelationshipMemory ? '开' : '关' }} / 偏好 {{ testDebugDisplay.usedPreferenceMemory ? '开' : '关' }}）
                          </span>
                        </div>
                        <div>
                          记忆更新：{{ testDebugDisplay.memoryUpdateReason }}
                          <span v-if="testDebugDisplay.cooldownActive" class="text-[#7b857f]">（冷却中）</span>
                        </div>
                        <div>Runtime：{{ testDebugDisplay.runtimeSource }}</div>
                        <div>Fallback：{{ testDebugDisplay.fallbackUsed ? '是' : '否' }}</div>
                        <div v-if="testDebugDisplay.errorTag">错误标签：{{ testDebugDisplay.errorTag }}</div>
                      </div>
                      <div v-else class="mt-3 text-[#7b857f]">
                        先试聊一次，这里会显示 prompt layers、记忆注入和 fallback 状态。
                      </div>
                    </div>

                    <div class="mt-4 rounded-[22px] border border-[#e7e0d4] bg-[#fcfbf7] p-4 text-sm">
                      <div class="text-xs font-bold uppercase tracking-[0.16em] text-[#7c6d55]">最近一次调试摘要</div>
                      <div v-if="recentDebugSummary" class="mt-3 space-y-2 text-[#4d5953]">
                        <div class="font-semibold text-[#16231f]">{{ recentDebugSummary.character_name }}</div>
                        <div>记忆模式：{{ recentDebugSummary.memory_mode }}</div>
                        <div>音色：{{ recentDebugSummary.voice_name || '未配置' }}</div>
                        <div>Prompt Layers：{{ recentDebugSummary.prompt_layers.join(' / ') || '尚未记录' }}</div>
                        <div>Runtime：{{ recentDebugSummary.runtime_source || '尚未记录' }}</div>
                        <div>Fallback：{{ recentDebugSummary.fallback_used ? '是' : '否' }}</div>
                        <div>记忆更新：{{ recentDebugSummary.memory_update_reason || '尚未记录' }}</div>
                        <div>摘要注入：{{ recentDebugSummary.used_summary ? '是' : '否' }}</div>
                        <div>关系记忆注入：{{ recentDebugSummary.used_relationship_memory ? '是' : '否' }}</div>
                        <div>偏好记忆注入：{{ recentDebugSummary.used_user_preference_memory ? '是' : '否' }}</div>
                        <div v-if="recentDebugSummary.error_tag">错误标签：{{ recentDebugSummary.error_tag }}</div>
                      </div>
                      <div v-else class="mt-3 text-[#7b857f]">
                        当前还没有历史调试摘要。
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

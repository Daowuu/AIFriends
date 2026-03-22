<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import api from '@/api/http'
import streamApi from '@/api/streamApi'
import AppIcon from '@/components/AppIcon.vue'
import CharacterForm from '@/components/CharacterForm.vue'
import MarkdownContent from '@/components/MarkdownContent.vue'
import CharacterCard from '@/components/character/CharacterCard.vue'
import ApiSettingsView from '@/views/ApiSettingsView.vue'
import type { Character, CharacterFormPayload, VoiceOption } from '@/types/character'
import type { StudioChatDebug, StudioOverview, StudioRecentDebugSummary } from '@/types/studio'
import { useCharacterChatNavigation } from '@/utils/useCharacterChatNavigation'

type CharacterFormStudioExpose = {
  previewVoiceFromCurrentDraft: (text?: string) => Promise<void>
  stopVoicePreview: () => void
}

const studioTab = ref<'workflow' | 'settings'>('workflow')
const workspacePanel = ref<'configure' | 'overview' | 'diagnostics'>('configure')
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
    || character.custom_prompt.toLowerCase().includes(query)
  ))
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

const diagnosticSummary = computed(() => {
  const summary = runtimeSummary.value
  if (!summary) return null

  if (summary.chat_runtime_status === 'invalid') {
    const actionMap: Record<string, string> = {
      local_missing_api_key: '到运行时配置里补全聊天 API Key，然后重新试聊。',
      local_missing_api_base: '到运行时配置里补全聊天 API Base。',
      local_missing_model_name: '到运行时配置里补全聊天模型名。',
    }
    return {
      level: 'warning',
      title: '本地聊天配置不完整',
      detail: summary.chat_runtime_reason || '当前本地聊天配置不可用。',
      action: actionMap[summary.chat_runtime_reason] || '检查运行时配置后重新试聊。',
    }
  }

  if (summary.chat_runtime_status === 'missing') {
    return {
      level: 'info',
      title: '当前没有可用的聊天模型配置',
      detail: '系统会退回本地保底回复，适合调 UI，不适合做正式角色试聊。',
      action: '去“运行时配置”补一套聊天模型配置，再回来试聊。',
    }
  }

  return {
    level: 'success',
    title: '聊天运行态正常',
    detail: `当前会优先使用 ${summary.chat_runtime.label}。`,
    action: summary.chat_runtime.api_base
      ? `当前网关：${summary.chat_runtime.api_base}`
      : '可以直接开始试聊或进入正式聊天。',
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
      selectedCharacterId.value = response.data.characters[0]?.id ?? null
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
      const response = await api.post<{ character: Character }>('/character/create/', formData)
      hasDraftSlot.value = false
      await loadStudioOverview(response.data.character.id)
    } else if (currentCharacter.value) {
      const response = await api.post<{ character: Character }>(`/character/${currentCharacter.value.id}/update/`, formData)
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
  if (typeof window !== 'undefined' && !window.confirm(`删除角色“${character.name}”后将同时移除这段会话记录。是否继续？`)) {
    return
  }

  pending.value = true
  overviewError.value = ''

  try {
    await api.post(`/character/${character.id}/remove/`)
    await loadStudioOverview(character.id === selectedCharacterId.value ? null : selectedCharacterId.value)
    workspacePanel.value = 'configure'
    hasDraftSlot.value = false
  } catch (error: unknown) {
    overviewError.value = '删除角色失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      overviewError.value = response?.data?.detail || overviewError.value
    }
  } finally {
    pending.value = false
  }
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

const runTrialChat = async () => {
  if (!currentCharacter.value?.id) {
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
    let debugResult: StudioChatDebug | null = null

    await streamApi({
      url: '/session/chat/',
      body: {
        character_id: currentCharacter.value.id,
        message: prompt,
      },
      onmessage(json, done) {
        if (json.error) {
          testError.value = json.error
          return
        }
        if (json.content) testReply.value += json.content
        if (json.meta?.debug) {
          debugResult = json.meta.debug as StudioChatDebug
          testDebug.value = debugResult
        }
        if (done) testPending.value = false
      },
      onerror(error) {
        testPending.value = false
        testError.value = error instanceof Error ? error.message : '试聊失败。'
      },
    })

    const latestDebug = debugResult as StudioChatDebug | null

    if (currentCharacter.value) {
      recentDebugSummary.value = {
        session_id: recentDebugSummary.value?.session_id || 0,
        character_id: currentCharacter.value.id,
        character_name: currentCharacter.value.name,
        memory_mode: currentCharacter.value.ai_config.memory_mode,
        voice_name: currentCharacter.value.voice?.name || '',
        last_message_at: new Date().toISOString(),
        memory_updated_at: recentDebugSummary.value?.memory_updated_at || '',
        last_debug_at: new Date().toISOString(),
        has_summary: latestDebug?.memory_injection.used_summary ?? false,
        has_preference_memory: latestDebug?.memory_injection.used_user_preference_memory ?? false,
        prompt_layers: latestDebug?.prompt_layers || [],
        runtime_source: latestDebug?.runtime_source || '',
        fallback_used: latestDebug?.fallback_used ?? false,
        error_tag: latestDebug?.error_tag || '',
        memory_update_reason: latestDebug?.memory_update.reason || '',
        memory_update_triggered: latestDebug?.memory_update.triggered ?? false,
        used_summary: latestDebug?.memory_injection.used_summary ?? false,
        used_relationship_memory: latestDebug?.memory_injection.used_relationship_memory ?? false,
        used_user_preference_memory: latestDebug?.memory_injection.used_user_preference_memory ?? false,
      }
    }
    await loadStudioOverview(currentCharacter.value.id)
  } catch (error: unknown) {
    testError.value = error instanceof Error ? error.message : '试聊失败。'
    testPending.value = false
  } finally {
    if (testPending.value) testPending.value = false
  }
}

const handleStudioMemoryReset = async () => {
  if (!currentCharacter.value?.id || memoryActionPending.value) return
  if (typeof window !== 'undefined' && !window.confirm('清空长期记忆会移除这段会话的摘要、关系记忆和用户偏好记忆。是否继续？')) return

  memoryActionPending.value = true
  memoryActionMessage.value = ''
  memoryActionError.value = ''

  try {
    const response = await api.post<{ detail: string }>('/session/reset/', {
      character_id: currentCharacter.value.id,
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
  } catch (error) {
    studioVoicePreviewError.value = error instanceof Error ? error.message : '语音试听失败。'
  } finally {
    studioVoicePreviewPending.value = false
  }
}

const openChat = async (character: Character) => {
  await openCharacterChat(character)
}

onMounted(() => {
  void loadStudioOverview()
})
</script>

<template>
  <section class="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 xl:px-8">
    <div class="rounded-[34px] border border-[#ded4c3] bg-[linear-gradient(135deg,rgba(255,251,243,0.95),rgba(247,243,234,0.92))] p-6 shadow-[0_30px_90px_-42px_rgba(15,23,42,0.24)]">
      <div class="flex flex-col gap-4 border-b border-[#e6ddcd] pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div class="inline-flex rounded-full bg-[#16231f] px-3 py-1 text-xs font-black uppercase tracking-[0.2em] text-[#f7f1e5]">
            AI Studio
          </div>
          <h1 class="mt-4 text-3xl font-black tracking-tight text-[#15231f] sm:text-4xl">角色定义、运行时配置、试聊与试听</h1>
          <p class="mt-3 max-w-3xl text-sm leading-7 text-[#56635d]">
            这里是单实例角色工作台。你可以创建角色、编辑 Prompt、调整模型与语音配置，然后直接试聊和试听。
          </p>
        </div>

        <div class="flex flex-wrap gap-3">
          <button class="btn rounded-full border-[#d6ccb8] bg-white/80 text-[#15231f] hover:bg-[#fff7e8]" @click="studioTab = 'workflow'">
            角色工作流
          </button>
          <button class="btn rounded-full border-[#d6ccb8] bg-white/80 text-[#15231f] hover:bg-[#fff7e8]" @click="studioTab = 'settings'">
            运行时配置
          </button>
        </div>
      </div>

      <div v-if="overviewError" class="alert alert-error mt-6">{{ overviewError }}</div>

      <div v-if="loading" class="grid min-h-[360px] place-items-center">
        正在加载 Studio...
      </div>

      <template v-else>
        <div v-if="studioTab === 'workflow'" class="mt-6 space-y-6">
          <div class="rounded-[28px] border border-[#dfd4c1] bg-white/72 p-4">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div class="min-w-0 flex-1">
                <div class="text-xs font-black uppercase tracking-[0.2em] text-[#8a7757]">角色切换</div>
                <div class="mt-3 flex gap-3 overflow-x-auto pb-2">
                  <button
                    v-for="character in filteredCharacters"
                    :key="character.id"
                    type="button"
                    class="flex min-w-[200px] items-center gap-3 rounded-[22px] border px-4 py-3 text-left transition"
                    :class="selectedCharacterId === character.id ? 'border-[#16231f] bg-[#16231f] text-[#f7f1e5]' : 'border-[#d9cfbe] bg-white text-[#22302b] hover:bg-[#fff7e8]'"
                    @click="selectCharacter(character)"
                  >
                    <div class="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-2xl bg-base-200 font-black">
                      <img v-if="character.photo" :src="character.photo" :alt="character.name" class="h-full w-full object-cover">
                      <span v-else>{{ character.name.slice(0, 1) }}</span>
                    </div>
                    <div class="min-w-0">
                      <div class="truncate font-black">{{ character.name }}</div>
                      <div class="truncate text-xs opacity-70">{{ character.ai_config.reply_style }} · {{ character.ai_config.memory_mode }}</div>
                    </div>
                  </button>

                  <button
                    type="button"
                    class="flex min-w-[200px] items-center gap-3 rounded-[22px] border border-dashed border-[#ccbfa8] bg-[#fbf5e8] px-4 py-3 text-left text-[#5f543f] transition hover:bg-[#fff7e8]"
                    @click="startCreateMode"
                  >
                    <span class="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-white text-xl font-black">+</span>
                    <div>
                      <div class="font-black">新角色</div>
                      <div class="text-xs opacity-70">创建一个新的角色草稿</div>
                    </div>
                  </button>
                </div>
              </div>

              <div class="flex items-center gap-3">
                <label class="flex h-11 items-center gap-2 rounded-full border border-[#d9cdb6] bg-white/86 px-4">
                  <AppIcon name="search" icon-class="h-4 w-4 text-[#7e6e56]" />
                  <input v-model="searchQuery" type="text" class="bg-transparent text-sm font-semibold outline-none" placeholder="搜索角色">
                </label>
                <div class="rounded-full border border-[#d6ccb8] bg-white/80 px-4 py-2 text-sm font-bold text-[#45554d]">
                  {{ characters.length }} 个角色
                </div>
              </div>
            </div>
          </div>

          <div class="flex gap-3">
            <button class="btn rounded-full border-[#d6ccb8] bg-white/80 text-[#15231f] hover:bg-[#fff7e8]" @click="workspacePanel = 'configure'">
              角色配置
            </button>
            <button class="btn rounded-full border-[#d6ccb8] bg-white/80 text-[#15231f] hover:bg-[#fff7e8]" @click="workspacePanel = 'overview'">
              角色概览
            </button>
            <button class="btn rounded-full border-[#d6ccb8] bg-white/80 text-[#15231f] hover:bg-[#fff7e8]" @click="workspacePanel = 'diagnostics'">
              试聊诊断
            </button>
          </div>

          <div v-show="workspacePanel === 'configure'" class="space-y-6">
            <div class="rounded-[32px] border border-[#ded4c3] bg-white/78 p-6 shadow-sm">
              <div v-if="currentCharacter" class="mb-6 flex flex-wrap items-center justify-between gap-3 border-b border-[#e6ddcd] pb-4">
                <div>
                  <div class="text-xs font-black uppercase tracking-[0.2em] text-[#8a7757]">当前角色</div>
                  <div class="mt-2 text-xl font-black text-[#15231f]">{{ currentCharacter.name }}</div>
                </div>
                <button
                  type="button"
                  class="btn rounded-full border border-error/30 bg-error/5 text-error hover:bg-error/10"
                  :disabled="pending"
                  @click="removeCharacter(currentCharacter)"
                >
                  {{ pending ? '处理中...' : '删除角色' }}
                </button>
              </div>

              <CharacterForm
                :key="formKey"
                ref="characterFormRef"
                :mode="editorMode"
                :initial-character="currentCharacter"
                :voices="voices"
                :pending="pending"
                :show-voice-preview="false"
                @submit="handleSubmit"
                @voices-changed="loadStudioOverview(currentCharacter?.id)"
              />
            </div>
          </div>

          <div v-show="workspacePanel === 'diagnostics'" class="space-y-6">
            <div class="rounded-[32px] border border-[#ded4c3] bg-white/78 p-6 shadow-sm">
              <div class="border-b border-[#e6ddcd] pb-4">
                <h2 class="text-2xl font-black text-[#15231f]">试聊与诊断</h2>
                <p class="mt-2 text-sm leading-6 text-[#56635d]">试聊会直接使用当前角色的长期会话与运行时配置，并回显本轮诊断摘要。</p>
              </div>

              <div class="mt-6 space-y-5">
                <div>
                  <label class="block text-sm font-black text-[#22302b]">试聊输入</label>
                  <textarea v-model="testPrompt" class="textarea textarea-bordered mt-3 min-h-32 w-full bg-white" placeholder="输入一句测试话术，看看角色会怎么回应。" />
                </div>

                <div class="flex flex-wrap gap-3">
                  <button class="btn rounded-full border-none bg-[#16231f] text-[#f7f1e5] hover:bg-[#22362f]" :disabled="testPending || !currentCharacter?.id" @click="runTrialChat">
                    {{ testPending ? '试聊中...' : '开始试聊' }}
                  </button>
                  <button class="btn rounded-full border-[#d6ccb8] bg-white/80 text-[#15231f] hover:bg-[#fff7e8]" :disabled="studioVoicePreviewPending" @click="handleStudioVoicePreview">
                    {{ studioVoicePreviewPending ? '试听中...' : '试试音色' }}
                  </button>
                  <button class="btn rounded-full border-[#d6ccb8] bg-white/80 text-error hover:bg-[#fff7e8]" :disabled="!currentCharacter?.id || memoryActionPending" @click="handleStudioMemoryReset">
                    {{ memoryActionPending ? '清空中...' : '清空长期记忆' }}
                  </button>
                </div>

                <div v-if="testError" class="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">{{ testError }}</div>
                <div v-if="studioVoicePreviewError" class="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">{{ studioVoicePreviewError }}</div>
                <div v-if="memoryActionMessage" class="rounded-2xl border border-success/20 bg-success/5 px-4 py-3 text-sm text-success">{{ memoryActionMessage }}</div>
                <div v-if="memoryActionError" class="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">{{ memoryActionError }}</div>

                <div class="rounded-[26px] border border-[#dfd4c1] bg-[#fcfbf7] p-5">
                  <div class="text-sm font-black text-[#22302b]">试聊回复</div>
                  <div v-if="testReply" class="mt-4 prose max-w-none text-sm leading-7 text-[#32413b]">
                    <MarkdownContent :content="testReply" />
                  </div>
                  <div v-else class="mt-4 text-sm text-[#7d7568]">还没有试聊结果。</div>
                </div>
              </div>
            </div>

            <div class="grid gap-4 xl:grid-cols-2">
              <div class="rounded-[28px] border border-[#ded4c3] bg-white/78 p-5 shadow-sm">
                <div class="text-xs font-black uppercase tracking-[0.2em] text-[#8a7757]">实时调试</div>
                <div v-if="testDebugDisplay" class="mt-4 space-y-3 text-sm text-[#45554d]">
                  <div><span class="font-black text-[#15231f]">Prompt Layers</span> · {{ testDebugDisplay.promptLayers }}</div>
                  <div><span class="font-black text-[#15231f]">记忆模式</span> · {{ testDebugDisplay.memoryMode }}</div>
                  <div><span class="font-black text-[#15231f]">记忆注入</span> · 摘要 {{ testDebugDisplay.usedSummary ? '是' : '否' }} / 关系 {{ testDebugDisplay.usedRelationshipMemory ? '是' : '否' }} / 偏好 {{ testDebugDisplay.usedPreferenceMemory ? '是' : '否' }}</div>
                  <div><span class="font-black text-[#15231f]">本轮刷新</span> · {{ testDebugDisplay.memoryUpdateReason }}</div>
                  <div><span class="font-black text-[#15231f]">Runtime</span> · {{ testDebugDisplay.runtimeSource }}</div>
                  <div><span class="font-black text-[#15231f]">Fallback</span> · {{ testDebugDisplay.fallbackUsed ? '是' : '否' }}</div>
                  <div v-if="testDebugDisplay.errorTag"><span class="font-black text-[#15231f]">错误标签</span> · {{ testDebugDisplay.errorTag }}</div>
                </div>
                <div v-else class="mt-4 text-sm text-[#7d7568]">还没有本轮试聊调试信息。</div>
              </div>

              <div class="rounded-[28px] border border-[#ded4c3] bg-white/78 p-5 shadow-sm">
                <div class="text-xs font-black uppercase tracking-[0.2em] text-[#8a7757]">最近实验摘要</div>
                <div v-if="recentDebugSummary" class="mt-4 space-y-3 text-sm text-[#45554d]">
                  <div><span class="font-black text-[#15231f]">角色</span> · {{ recentDebugSummary.character_name }}</div>
                  <div><span class="font-black text-[#15231f]">Prompt Layers</span> · {{ recentDebugSummary.prompt_layers.join(' / ') || '无' }}</div>
                  <div><span class="font-black text-[#15231f]">Runtime</span> · {{ recentDebugSummary.runtime_source || '无' }}</div>
                  <div><span class="font-black text-[#15231f]">记忆注入</span> · 摘要 {{ recentDebugSummary.used_summary ? '是' : '否' }} / 偏好 {{ recentDebugSummary.used_user_preference_memory ? '是' : '否' }}</div>
                  <div><span class="font-black text-[#15231f]">刷新原因</span> · {{ recentDebugSummary.memory_update_reason || '无' }}</div>
                </div>
                <div v-else class="mt-4 text-sm text-[#7d7568]">当前还没有最近一次实验摘要。</div>
              </div>
            </div>
          </div>

          <div v-show="workspacePanel === 'overview'" class="grid gap-4 xl:grid-cols-2">
            <CharacterCard
              v-if="currentCharacter"
              :character="currentCharacter"
              mode="studio"
              @edit="selectCharacter"
              @chat="openChat"
              @remove="removeCharacter"
            />

            <div class="rounded-[28px] border border-[#ded4c3] bg-white/78 p-5 shadow-sm">
              <div class="text-xs font-black uppercase tracking-[0.2em] text-[#8a7757]">运行时摘要</div>
              <div v-if="diagnosticSummary" class="mt-4 space-y-3">
                <div class="text-lg font-black text-[#15231f]">{{ diagnosticSummary.title }}</div>
                <p class="text-sm leading-6 text-[#56635d]">{{ diagnosticSummary.detail }}</p>
                <div class="rounded-2xl border border-[#e7dece] bg-[#fbf7ef] px-4 py-3 text-sm text-[#5f543f]">
                  {{ diagnosticSummary.action }}
                </div>
              </div>
              <div v-else class="mt-4 text-sm text-[#7d7568]">当前还没有运行时摘要。</div>
            </div>
          </div>
        </div>

        <div v-else class="mt-6">
          <ApiSettingsView embedded />
        </div>
      </template>
    </div>
  </section>
</template>

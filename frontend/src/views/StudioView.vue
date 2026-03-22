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
import type { StudioOverview, StudioSessionMemorySummary } from '@/types/studio'
import { useCharacterChatNavigation } from '@/utils/useCharacterChatNavigation'

type CharacterFormStudioExpose = {
  getVoicePreviewValidationError: () => string
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
const sessionMemorySummaries = ref<StudioSessionMemorySummary[]>([])
const selectedCharacterId = ref<number | null>(null)
const hasDraftSlot = ref(false)
const draftSlotVersion = ref(0)
const reorderPending = ref(false)
const draggedCharacterId = ref<number | null>(null)
const searchQuery = ref('')
const testPrompt = ref('用你的角色语气做一个简短自我介绍。')
const testReply = ref('')
const testPending = ref(false)
const testError = ref('')
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

const reorderCharactersLocally = (sourceId: number, targetId: number) => {
  if (sourceId === targetId) return false

  const sourceIndex = characters.value.findIndex((character) => character.id === sourceId)
  const targetIndex = characters.value.findIndex((character) => character.id === targetId)
  if (sourceIndex < 0 || targetIndex < 0) return false

  const nextCharacters = [...characters.value]
  const [movedCharacter] = nextCharacters.splice(sourceIndex, 1)
  if (!movedCharacter) return false
  nextCharacters.splice(targetIndex, 0, movedCharacter)
  characters.value = nextCharacters.map((character, index) => ({
    ...character,
    sort_order: index,
  }))
  return true
}

const persistCharacterOrder = async (previousCharacters: Character[]) => {
  try {
    const response = await api.post<{ characters: Character[] }>('/character/reorder/', {
      character_ids: characters.value.map((character) => character.id),
    })
    characters.value = response.data.characters
  } catch (error: unknown) {
    characters.value = previousCharacters
    overviewError.value = '保存角色顺序失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      overviewError.value = response?.data?.detail || overviewError.value
    }
  } finally {
    reorderPending.value = false
  }
}

const handleCharacterDragStart = (characterId: number) => {
  if (reorderPending.value) return
  draggedCharacterId.value = characterId
}

const handleCharacterDragEnd = () => {
  draggedCharacterId.value = null
}

const handleCharacterDrop = async (targetCharacterId: number) => {
  const sourceCharacterId = draggedCharacterId.value
  draggedCharacterId.value = null

  if (!sourceCharacterId || sourceCharacterId === targetCharacterId || reorderPending.value) {
    return
  }

  const previousCharacters = [...characters.value]
  const changed = reorderCharactersLocally(sourceCharacterId, targetCharacterId)
  if (!changed) return

  reorderPending.value = true
  overviewError.value = ''
  await persistCharacterOrder(previousCharacters)
}

const currentSessionMemorySummary = computed(() => {
  if (!currentCharacter.value?.id) return null
  return sessionMemorySummaries.value.find((item) => item.character_id === currentCharacter.value?.id) ?? null
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

const voiceDiagnosticSummary = computed(() => {
  const summary = runtimeSummary.value
  if (!summary?.tts_runtime?.enabled) {
    return {
      level: 'warning',
      title: '语音运行时还没准备好',
      detail: '当前实例还没有可用的语音 key 或播报配置，所以音色试听无法工作。',
      action: '去“运行时配置”补全语音 API Key、识别模型和播报模型，然后再回来试听。',
    }
  }

  return {
    level: 'success',
    title: '语音运行态正常',
    detail: `当前试听会使用 ${summary.tts_runtime.label}。`,
    action: summary.tts_runtime.api_base
      ? `当前语音网关：${summary.tts_runtime.api_base}`
      : '可以直接试听当前角色音色。',
  }
})

const trialChatStatusSummary = computed(() => {
  const summary = runtimeSummary.value
  if (!currentCharacter.value?.id) {
    return {
      title: '试聊还没准备好',
      detail: '当前是新角色草稿状态，先保存角色后才能进入正式试聊。',
      action: '先完成角色配置并保存，再回来试聊。',
    }
  }

  if (!summary) {
    return {
      title: '试聊状态暂时不可用',
      detail: '运行时摘要还没加载完成。',
      action: '稍后重试，或刷新 Studio 页面。',
    }
  }

  if (testPending.value) {
    return {
      title: '试聊进行中',
      detail: '当前正在请求聊天模型并等待角色回复。',
      action: '等这一轮完成后，再看回复结果。',
    }
  }

  if (summary.chat_runtime_status === 'invalid') {
    return {
      title: '聊天运行时配置不完整',
      detail: '当前聊天配置无法正常工作，所以试聊不会成功。',
      action: '去“运行时配置”补全聊天 API Key、API Base 和模型名。',
    }
  }

  if (summary.chat_runtime_status === 'missing') {
    return {
      title: '当前没有聊天模型配置',
      detail: '现在只能显示本地保底回复，不适合判断角色真实效果。',
      action: '先在“运行时配置”里保存一套聊天配置，再回来试聊。',
    }
  }

  if (testError.value) {
    return {
      title: '上一轮试聊失败',
      detail: testError.value,
      action: '调整输入或检查运行时配置后再试一次。',
    }
  }

  if (testReply.value.trim()) {
    return {
      title: '试聊已完成',
      detail: '当前角色已经返回一轮回复，可以根据结果继续调 Prompt、记忆模式或语气设定。',
      action: '如果语气不对，就回到“角色配置”继续微调。',
    }
  }

  return {
    title: '试聊可以开始',
    detail: `当前会使用 ${summary.chat_runtime.label} 进行角色回复生成。`,
    action: '输入一句测试话术，看看角色会怎么回应。',
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
    sessionMemorySummaries.value = response.data.session_memory_summaries

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
}

const selectCharacter = (character: Character) => {
  selectedCharacterId.value = character.id
  workspacePanel.value = 'configure'
  testReply.value = ''
  testError.value = ''
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

  try {
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
        if (done) testPending.value = false
      },
      onerror(error) {
        testPending.value = false
        testError.value = error instanceof Error ? error.message : '试聊失败。'
      },
    })

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
  if (!characterFormRef.value) {
    studioVoicePreviewError.value = '当前角色表单还没准备好，请稍后再试。'
    return
  }

  if (!runtimeSummary.value?.tts_runtime?.enabled) {
    studioVoicePreviewError.value = '当前语音运行时未启用。请先到“运行时配置”补全语音 API Key 和播报模型。'
    return
  }

  const validationError = characterFormRef.value.getVoicePreviewValidationError()
  if (validationError) {
    studioVoicePreviewError.value = validationError
    return
  }

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
  <section class="mx-auto w-full max-w-[104rem] px-4 py-6 sm:px-6 xl:px-8">
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
          <RouterLink
            to="/discussion"
            class="btn rounded-full border-[#d6ccb8] bg-white/80 text-[#15231f] hover:bg-[#fff7e8]"
          >
            讨论组工作台
          </RouterLink>
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
                    draggable="true"
                    class="flex min-w-[11rem] items-center gap-3 rounded-[22px] border px-4 py-3 text-left transition sm:min-w-[12rem] xl:min-w-[13rem]"
                    :class="selectedCharacterId === character.id ? 'border-[#16231f] bg-[#16231f] text-[#f7f1e5]' : 'border-[#d9cfbe] bg-white text-[#22302b] hover:bg-[#fff7e8]'"
                    @click="selectCharacter(character)"
                    @dragstart="handleCharacterDragStart(character.id)"
                    @dragend="handleCharacterDragEnd"
                    @dragover.prevent
                    @drop="handleCharacterDrop(character.id)"
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
                    class="flex min-w-[11rem] items-center gap-3 rounded-[22px] border border-dashed border-[#ccbfa8] bg-[#fbf5e8] px-4 py-3 text-left text-[#5f543f] transition hover:bg-[#fff7e8] sm:min-w-[12rem] xl:min-w-[13rem]"
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
                  {{ reorderPending ? '保存顺序中...' : `${characters.length} 个角色` }}
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
            <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <section class="rounded-[32px] border border-[#ded4c3] bg-white/78 p-6 shadow-sm">
                <div class="border-b border-[#e6ddcd] pb-4">
                  <h2 class="text-2xl font-black text-[#15231f]">试聊</h2>
                  <p class="mt-2 text-sm leading-6 text-[#56635d]">试聊会直接使用当前角色的长期会话与聊天运行时，用来判断角色语气和回复走向。</p>
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
                    <button class="btn rounded-full border-[#d6ccb8] bg-white/80 text-error hover:bg-[#fff7e8]" :disabled="!currentCharacter?.id || memoryActionPending" @click="handleStudioMemoryReset">
                      {{ memoryActionPending ? '清空中...' : '清空长期记忆' }}
                    </button>
                  </div>

                  <div v-if="testError" class="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">{{ testError }}</div>
                  <div v-if="memoryActionMessage" class="rounded-2xl border border-success/20 bg-success/5 px-4 py-3 text-sm text-success">{{ memoryActionMessage }}</div>
                  <div v-if="memoryActionError" class="rounded-2xl border border-error/20 bg-error/5 px-4 py-3 text-sm text-error">{{ memoryActionError }}</div>

                  <div class="rounded-[28px] border border-[#ded4c3] bg-[#fcfbf7] p-5">
                    <div class="text-xs font-black uppercase tracking-[0.2em] text-[#8a7757]">试聊状态</div>
                    <div class="mt-4">
                      <div class="text-lg font-black text-[#15231f]">{{ trialChatStatusSummary.title }}</div>
                      <p class="mt-2 text-sm leading-6 text-[#56635d]">{{ trialChatStatusSummary.detail }}</p>
                      <div class="mt-3 rounded-2xl border border-[#e7dece] bg-[#fbf7ef] px-4 py-3 text-sm text-[#5f543f]">
                        {{ trialChatStatusSummary.action }}
                      </div>
                    </div>
                  </div>

                  <div class="rounded-[28px] border border-[#dfd4c1] bg-[#fcfbf7] p-5">
                    <div class="text-sm font-black text-[#22302b]">试聊输出</div>
                    <div v-if="testReply" class="mt-4 prose max-w-none text-sm leading-7 text-[#32413b]">
                      <MarkdownContent :content="testReply" />
                    </div>
                    <div v-else class="mt-4 text-sm text-[#7d7568]">还没有试聊结果。</div>
                  </div>
                </div>
              </section>

              <section class="rounded-[32px] border border-[#ded4c3] bg-white/78 p-6 shadow-sm">
                <div class="border-b border-[#e6ddcd] pb-4">
                  <h2 class="text-2xl font-black text-[#15231f]">试听</h2>
                  <p class="mt-2 text-sm leading-6 text-[#56635d]">试听会直接使用当前草稿里的音色配置和语音运行时，用来确认真实播报效果。</p>
                </div>

                <div class="mt-6 space-y-5">
                  <div>
                    <label class="block text-sm font-black text-[#22302b]">音色试听文本</label>
                    <textarea
                      v-model="voiceSampleText"
                      class="textarea textarea-bordered mt-3 min-h-24 w-full bg-white"
                      placeholder="输入一段你想试听的文本，看看这个角色音色实际会怎么说。"
                    />
                  </div>

                  <div class="flex flex-wrap gap-3">
                    <button class="btn rounded-full border-[#d6ccb8] bg-white/80 text-[#15231f] hover:bg-[#fff7e8]" :disabled="studioVoicePreviewPending || !characterFormRef" @click="handleStudioVoicePreview">
                      {{ studioVoicePreviewPending ? '试听中...' : '试试音色' }}
                    </button>
                  </div>

                  <div
                    v-if="studioVoicePreviewError"
                    class="rounded-[24px] border border-error/30 bg-[linear-gradient(135deg,rgba(254,242,242,0.95),rgba(255,247,237,0.9))] px-5 py-4 text-sm text-error shadow-sm"
                  >
                    <div class="font-black">音色试听失败</div>
                    <div class="mt-2 leading-6">{{ studioVoicePreviewError }}</div>
                  </div>

                  <div class="rounded-[28px] border border-[#ded4c3] bg-[#fcfbf7] p-5">
                    <div class="text-xs font-black uppercase tracking-[0.2em] text-[#8a7757]">试听状态</div>
                    <div class="mt-4">
                      <div class="text-lg font-black text-[#15231f]">{{ voiceDiagnosticSummary.title }}</div>
                      <p class="mt-2 text-sm leading-6 text-[#56635d]">{{ voiceDiagnosticSummary.detail }}</p>
                      <div class="mt-3 rounded-2xl border border-[#e7dece] bg-[#fbf7ef] px-4 py-3 text-sm text-[#5f543f]">
                        {{ voiceDiagnosticSummary.action }}
                      </div>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </div>

          <div v-show="workspacePanel === 'overview'" class="grid gap-5 xl:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)]">
            <CharacterCard
              v-if="currentCharacter"
              :character="currentCharacter"
              mode="studio"
              @edit="selectCharacter"
              @chat="openChat"
              @remove="removeCharacter"
            />

            <div class="space-y-4">
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

              <div class="rounded-[28px] border border-[#ded4c3] bg-white/78 p-5 shadow-sm">
                <div class="text-xs font-black uppercase tracking-[0.2em] text-[#8a7757]">角色记忆</div>
                <div v-if="currentSessionMemorySummary" class="mt-4 space-y-4">
                  <div class="rounded-2xl border border-[#e7dece] bg-[#fcfbf7] px-4 py-3 text-sm text-[#5f543f]">
                    <div>最近消息：{{ currentSessionMemorySummary.last_message_at ? new Date(currentSessionMemorySummary.last_message_at).toLocaleString() : '还没有正式对话' }}</div>
                    <div class="mt-1">记忆更新时间：{{ currentSessionMemorySummary.memory_updated_at ? new Date(currentSessionMemorySummary.memory_updated_at).toLocaleString() : '还没形成长期记忆' }}</div>
                  </div>

                  <div class="space-y-3">
                    <div class="rounded-2xl border border-[#e7dece] bg-[#fcfbf7] p-4">
                      <div class="text-sm font-black text-[#15231f]">会话摘要</div>
                      <p class="mt-2 text-sm leading-6 text-[#56635d]">
                        {{ currentSessionMemorySummary.conversation_summary || '当前还没有稳定的会话摘要。多聊几轮之后，这里会开始沉淀角色与用户之间的重要上下文。' }}
                      </p>
                    </div>

                    <div class="rounded-2xl border border-[#e7dece] bg-[#fcfbf7] p-4">
                      <div class="text-sm font-black text-[#15231f]">关系记忆</div>
                      <p class="mt-2 text-sm leading-6 text-[#56635d]">
                        {{ currentSessionMemorySummary.relationship_memory || '当前还没有形成明确的关系记忆。角色会在长期对话中逐步沉淀和用户之间的关系感。' }}
                      </p>
                    </div>

                    <div class="rounded-2xl border border-[#e7dece] bg-[#fcfbf7] p-4">
                      <div class="text-sm font-black text-[#15231f]">用户偏好记忆</div>
                      <p class="mt-2 text-sm leading-6 whitespace-pre-line text-[#56635d]">
                        {{ currentSessionMemorySummary.user_preference_memory || '当前还没有沉淀出明确的用户偏好。聊得更多之后，这里会逐步出现称呼、偏好和话题倾向。' }}
                      </p>
                    </div>
                  </div>
                </div>
                <div v-else class="mt-4 text-sm text-[#7d7568]">当前角色还没有会话记忆摘要。</div>
              </div>
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

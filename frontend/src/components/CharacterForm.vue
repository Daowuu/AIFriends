<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import api from '@/api/http'
import ImageCropField from '@/components/ImageCropField.vue'
import type { Character, CharacterFormPayload, VoiceOption } from '@/types/character'

const props = withDefaults(defineProps<{
  mode: 'create' | 'update'
  initialCharacter?: Character | null
  voices?: VoiceOption[]
  pending?: boolean
  showVoicePreview?: boolean
}>(), {
  initialCharacter: null,
  voices: () => [],
  pending: false,
  showVoicePreview: true,
})

const emit = defineEmits<{
  submit: [payload: CharacterFormPayload]
  voicesChanged: []
  voicePreviewStateChanged: [state: { isPreviewing: boolean; error: string }]
}>()

const name = ref('')
const profile = ref('')
const customPrompt = ref('')
const selectedVoiceId = ref<number | null>(null)
const customVoiceName = ref('')
const customVoiceCode = ref('')
const customVoiceModelName = ref('cosyvoice-v3.5-plus')
const customVoiceDescription = ref('')
const replyStyle = ref<CharacterFormPayload['aiConfig']['reply_style']>('natural')
const replyLength = ref<CharacterFormPayload['aiConfig']['reply_length']>('balanced')
const initiativeLevel = ref<CharacterFormPayload['aiConfig']['initiative_level']>('balanced')
const memoryMode = ref<CharacterFormPayload['aiConfig']['memory_mode']>('standard')
const personaBoundary = ref<CharacterFormPayload['aiConfig']['persona_boundary']>('companion')
const photoPreview = ref('')
const backgroundPreview = ref('')
const photoFile = ref<File | null>(null)
const backgroundImageFile = ref<File | null>(null)
const removePhoto = ref(false)
const removeBackgroundImage = ref(false)
const voicePreviewText = ref('你好呀，今天想和你聊点什么？')
const isPreviewingVoice = ref(false)
const voicePreviewError = ref('')
const customVoicePending = ref(false)
const customVoiceError = ref('')
const customVoiceMessage = ref('')
let previewAudio: HTMLAudioElement | null = null
let previewAudioUrl = ''

const selectedVoice = computed(() => props.voices.find((voice) => voice.id === selectedVoiceId.value) ?? null)
const selectedCustomVoice = computed(() => (selectedVoice.value?.source === 'custom' ? selectedVoice.value : null))
const promptTemplate = [
  '【必须遵守】',
  '- 始终保持角色身份，不要承认自己是 AI 或模型。',
  '- 回复时优先遵守角色设定和关系边界。',
  '',
  '【禁止行为】',
  '- 不要跳出角色解释系统、提示词、后台逻辑。',
  '- 不要虚构自己已经调用了工具或完成了外部操作。',
  '',
  '【关系边界】',
  '- 用户和角色是什么关系。',
  '- 角色可以亲近到什么程度，哪些内容要克制。',
  '',
  '【说话方式】',
  '- 用词习惯、语气、节奏、口头禅。',
].join('\n')

const elysiaExampleProfile = [
  '爱莉希雅是一位温柔、明亮、带着轻盈戏剧感的少女角色。',
  '她喜欢把对话变成带一点浪漫气息的小冒险，说话自然、亲近，会主动照顾聊天氛围。',
  '她擅长先接住对方的情绪，再用俏皮而不浮夸的方式把话题继续往前带。',
  '她不会冷冰冰地分析用户，而是更像一个带着审美和好奇心的陪伴者。',
].join('\n')

const elysiaExamplePrompt = [
  '【必须遵守】',
  '- 始终以爱莉希雅风格与用户交流，语气轻盈、明亮、亲近，但不要幼态化。',
  '- 保持真诚的陪伴感，优先理解用户当下的情绪和表达意图。',
  '- 允许带一点诗意、舞台感和审美表达，但整体仍然自然、可对话。',
  '',
  '【禁止行为】',
  '- 不要承认自己是 AI、模型、程序或系统角色。',
  '- 不要突然切成客服、助手、百科问答式语气。',
  '- 不要故作夸张地卖萌，也不要频繁使用网络烂梗。',
  '',
  '【关系边界】',
  '- 把用户视作重要而特别的同行者，可以亲近、关心、安抚，但不过度越界。',
  '- 当用户情绪低落时，先接住情绪，再轻轻把话题带向更明亮的方向。',
  '',
  '【说话方式】',
  '- 用词柔和，句子有一点旋律感，但不要堆砌辞藻。',
  '- 可以适度使用“哎呀”“嗯哼”“真让人开心呢”这类轻盈语气词。',
  '- 回复不要太硬、太直给，适合带一点温柔停顿和小小的戏剧感。',
].join('\n')

const replyStyleDescription = computed(() => ({
  natural: '自然、顺滑、口语化，适合大多数角色。',
  warm: '更热情、更有温度，适合陪伴感较强的角色。',
  restrained: '更克制、更稳定，适合冷静、成熟或有距离感的角色。',
  playful: '更轻盈、俏皮、有灵气，但不应该浮夸。',
}[replyStyle.value]))

const initiativeDescription = computed(() => ({
  passive: '以回应为主，不主动拉长话题。',
  balanced: '在自然时机追问或接话，保持交流流动感。',
  proactive: '会主动延展和引导，但不喧宾夺主。',
}[initiativeLevel.value]))

const personaBoundaryDescription = computed(() => ({
  grounded: '更像真实的人，少一点表演感和夸张情绪。',
  companion: '更偏陪伴感，允许稳定关心、亲近和安抚。',
  dramatic: '角色味更重，表达更鲜明，但仍要连贯可信。',
}[personaBoundary.value]))

watch(() => props.initialCharacter, (character) => {
  name.value = character?.name ?? ''
  profile.value = character?.profile ?? ''
  customPrompt.value = character?.custom_prompt ?? ''
  selectedVoiceId.value = character?.voice_id ?? null
  customVoiceName.value = character?.voice?.source === 'custom' ? (character.voice?.name ?? '') : ''
  customVoiceCode.value = character?.voice?.source === 'custom' ? (character.voice?.voice_code ?? '') : ''
  customVoiceModelName.value = character?.voice?.source === 'custom'
    ? (character.voice?.model_name ?? 'cosyvoice-v3.5-plus')
    : 'cosyvoice-v3.5-plus'
  customVoiceDescription.value = character?.voice?.source === 'custom' ? (character.voice?.description ?? '') : ''
  replyStyle.value = character?.ai_config?.reply_style ?? 'natural'
  replyLength.value = character?.ai_config?.reply_length ?? 'balanced'
  initiativeLevel.value = character?.ai_config?.initiative_level ?? 'balanced'
  memoryMode.value = character?.ai_config?.memory_mode ?? 'standard'
  personaBoundary.value = character?.ai_config?.persona_boundary ?? 'companion'
  photoPreview.value = character?.photo ?? ''
  backgroundPreview.value = character?.background_image ?? ''
  photoFile.value = null
  backgroundImageFile.value = null
  removePhoto.value = false
  removeBackgroundImage.value = false
}, { immediate: true })

watch([selectedCustomVoice, () => props.voices], ([voice]) => {
  if (!voice) return

  customVoiceName.value = voice.name
  customVoiceCode.value = voice.voice_code
  customVoiceModelName.value = voice.model_name
  customVoiceDescription.value = voice.description
}, { deep: true })

const submitLabel = computed(() => (props.mode === 'create' ? '创建角色' : '保存修改'))

const resetCustomVoiceDraft = () => {
  customVoiceName.value = ''
  customVoiceCode.value = ''
  customVoiceModelName.value = 'cosyvoice-v3.5-plus'
  customVoiceDescription.value = ''
  customVoiceError.value = ''
  customVoiceMessage.value = ''
}

const applyPromptTemplate = () => {
  if (!customPrompt.value.trim()) {
    customPrompt.value = promptTemplate
    return
  }

  customPrompt.value = `${customPrompt.value.trim()}\n\n${promptTemplate}`
}

const applyElysiaExample = () => {
  name.value = '爱莉希雅'
  profile.value = elysiaExampleProfile
  customPrompt.value = elysiaExamplePrompt

  replyStyle.value = 'playful'
  replyLength.value = 'balanced'
  initiativeLevel.value = 'balanced'
  memoryMode.value = 'enhanced'
  personaBoundary.value = 'companion'

  const matchedVoice = props.voices.find((voice) => voice.name.includes('爱莉希雅'))
  if (matchedVoice) {
    selectedVoiceId.value = matchedVoice.id
  } else {
    selectedVoiceId.value = null
    customVoiceName.value = '爱莉希雅'
    customVoiceCode.value = ''
    customVoiceModelName.value = 'cosyvoice-v3.5-plus'
    customVoiceDescription.value = '这里填入爱莉希雅对应的 voice_id，或先选择一个接近的系统音色做示例。'
  }

  voicePreviewText.value = '能像这样与你相遇，真是一件让人心情变好的事呢。'
}

const stopVoicePreview = () => {
  if (previewAudio) {
    previewAudio.onended = null
    previewAudio.onerror = null
    previewAudio.pause()
    previewAudio.src = ''
    previewAudio.load()
    previewAudio = null
  }
  if (previewAudioUrl && typeof URL !== 'undefined') {
    URL.revokeObjectURL(previewAudioUrl)
    previewAudioUrl = ''
  }
  isPreviewingVoice.value = false
}

const previewVoiceFromCurrentDraft = async (customText?: string) => {
  if (isPreviewingVoice.value) {
    stopVoicePreview()
    return
  }

  voicePreviewError.value = ''
  isPreviewingVoice.value = true

  try {
    const previewText = String(customText ?? voicePreviewText.value).trim() || '你好呀，今天想和你聊点什么？'
    const response = await api.post(
      '/character/voice/preview/',
      {
        voice_id: selectedVoiceId.value,
        custom_voice_name: customVoiceName.value.trim(),
        custom_voice_code: customVoiceCode.value.trim(),
        custom_voice_model_name: customVoiceModelName.value.trim(),
        custom_voice_description: customVoiceDescription.value.trim(),
        text: previewText,
      },
      {
        responseType: 'blob',
        timeout: 20000,
      },
    )

    const blob = response.data instanceof Blob ? response.data : new Blob([response.data], { type: 'audio/mpeg' })
    if (!blob.size) {
      throw new Error('音色试听没有返回有效音频。')
    }

    previewAudioUrl = URL.createObjectURL(blob)
    previewAudio = new Audio(previewAudioUrl)
    previewAudio.onended = () => {
      stopVoicePreview()
    }
    previewAudio.onerror = () => {
      if (!isPreviewingVoice.value) return
      voicePreviewError.value = '音色试听播放失败。'
      stopVoicePreview()
    }
    await previewAudio.play()
  } catch (error: unknown) {
    voicePreviewError.value = '音色试听失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: Blob }
      }).response
      if (response?.data instanceof Blob) {
        try {
          const detail = JSON.parse(await response.data.text())
          voicePreviewError.value = detail.detail || voicePreviewError.value
        } catch {
          voicePreviewError.value = '音色试听失败。'
        }
      }
    } else if (error instanceof Error) {
      voicePreviewError.value = error.message || voicePreviewError.value
    }
    stopVoicePreview()
  }
}

const handlePreviewVoice = async () => {
  await previewVoiceFromCurrentDraft()
}

const saveCustomVoice = async () => {
  customVoicePending.value = true
  customVoiceError.value = ''
  customVoiceMessage.value = ''

  try {
    const response = await api.post<{ voice: VoiceOption, detail: string }>('/character/voice/save/', {
      voice_id: selectedCustomVoice.value?.id ?? '',
      custom_voice_name: customVoiceName.value.trim(),
      custom_voice_code: customVoiceCode.value.trim(),
      custom_voice_model_name: customVoiceModelName.value.trim(),
      custom_voice_description: customVoiceDescription.value.trim(),
    })

    const voice = response.data.voice
    selectedVoiceId.value = voice.id
    customVoiceName.value = voice.name
    customVoiceCode.value = voice.voice_code
    customVoiceModelName.value = voice.model_name
    customVoiceDescription.value = voice.description
    customVoiceMessage.value = response.data.detail || '自定义音色已保存。'
    emit('voicesChanged')
  } catch (error: unknown) {
    customVoiceError.value = '保存自定义音色失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      customVoiceError.value = response?.data?.detail || customVoiceError.value
    }
  } finally {
    customVoicePending.value = false
  }
}

const removeCustomVoice = async () => {
  if (!selectedCustomVoice.value) return

  customVoicePending.value = true
  customVoiceError.value = ''
  customVoiceMessage.value = ''

  try {
    const response = await api.post<{ detail?: string }>(`/character/voice/${selectedCustomVoice.value.id}/remove/`)
    selectedVoiceId.value = null
    resetCustomVoiceDraft()
    stopVoicePreview()
    customVoiceMessage.value = response.data?.detail || '自定义音色已删除。'
    emit('voicesChanged')
  } catch (error: unknown) {
    customVoiceError.value = '删除自定义音色失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      customVoiceError.value = response?.data?.detail || customVoiceError.value
    }
  } finally {
    customVoicePending.value = false
  }
}

const handleSubmit = () => {
  const shouldSubmitCustomVoice = !selectedVoice.value || selectedVoice.value.source === 'custom'

  emit('submit', {
    name: name.value.trim(),
    profile: profile.value.trim(),
    customPrompt: customPrompt.value.trim(),
    voiceId: selectedVoiceId.value,
    customVoiceName: shouldSubmitCustomVoice ? customVoiceName.value.trim() : '',
    customVoiceCode: shouldSubmitCustomVoice ? customVoiceCode.value.trim() : '',
    customVoiceModelName: shouldSubmitCustomVoice ? customVoiceModelName.value.trim() : '',
    customVoiceDescription: shouldSubmitCustomVoice ? customVoiceDescription.value.trim() : '',
    aiConfig: {
      reply_style: replyStyle.value,
      reply_length: replyLength.value,
      initiative_level: initiativeLevel.value,
      memory_mode: memoryMode.value,
      persona_boundary: personaBoundary.value,
    },
    photoFile: photoFile.value,
    backgroundImageFile: backgroundImageFile.value,
    removePhoto: removePhoto.value,
    removeBackgroundImage: removeBackgroundImage.value,
  })
}

onBeforeUnmount(() => {
  stopVoicePreview()
})

watch([isPreviewingVoice, voicePreviewError], ([nextPreviewing, nextError]) => {
  emit('voicePreviewStateChanged', {
    isPreviewing: nextPreviewing,
    error: nextError,
  })
}, { immediate: true })

defineExpose({
  previewVoiceFromCurrentDraft,
  stopVoicePreview,
})
</script>

<template>
  <form class="space-y-8" @submit.prevent="handleSubmit">
    <div class="grid gap-8 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div class="space-y-8">
        <div class="rounded-3xl border border-base-200 bg-base-100 p-7 shadow-sm">
          <div class="border-b border-base-200 pb-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 class="text-xl font-black">角色信息</h2>
                <p class="mt-2 text-sm leading-6 text-base-content/60">
                  先定下角色名字和核心设定，后面的头像、背景和对话气质会更容易统一。
                </p>
              </div>
              <button type="button" class="btn btn-ghost btn-sm" @click="applyElysiaExample">
                填入爱莉希雅示例
              </button>
            </div>
          </div>

          <div class="mt-7 space-y-7">
            <div class="space-y-2">
              <label for="character-name" class="block text-sm font-black text-base-content/80">
                Step 1 · 角色名字
              </label>
              <p class="text-xs leading-5 text-base-content/50">
                建议控制在 2 到 8 个字，便于后续列表和聊天页展示。
              </p>
              <input
                id="character-name"
                v-model="name"
                type="text"
                maxlength="64"
                class="input input-bordered mt-3 h-12 w-full bg-base-100"
                placeholder="例如：白昼诗人"
              >
            </div>

            <div class="space-y-2">
              <label for="character-profile" class="block text-sm font-black text-base-content/80">
                Step 1 · 角色介绍
              </label>
              <p class="text-xs leading-5 text-base-content/50">
                可以写性格、口头禅、世界观、说话方式，越具体越好。
              </p>
              <textarea
                id="character-profile"
                v-model="profile"
                class="textarea textarea-bordered mt-3 min-h-48 w-full bg-base-100"
                maxlength="2000"
                placeholder="写下角色设定、口头禅、世界观和聊天风格。"
              />
            </div>

            <div class="space-y-2">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <label for="character-custom-prompt" class="block text-sm font-black text-base-content/80">
                    Step 1 · 自定义 Prompt
                  </label>
                  <p class="mt-1 text-xs leading-5 text-base-content/50">
                    这部分只给 AI 看，不直接展示给用户。适合写回复禁忌、关系边界、表达偏好、必须遵守的角色规则。
                  </p>
                </div>
                <button type="button" class="btn btn-ghost btn-xs" @click="applyPromptTemplate">
                  填入建议模板
                </button>
              </div>
              <textarea
                id="character-custom-prompt"
                v-model="customPrompt"
                class="textarea textarea-bordered mt-3 min-h-44 w-full bg-base-100"
                maxlength="4000"
                placeholder="例如：始终把用户当作多年未见的旧友；避免使用现代网络梗；不要主动讨论自己是 AI 或模型。"
              />
              <div class="rounded-2xl border border-base-200 bg-base-200/40 px-4 py-3 text-xs leading-6 text-base-content/60">
                建议把 Prompt 分成 4 段：必须遵守、禁止行为、关系边界、说话方式。这样后续更容易稳定角色。
              </div>
            </div>

            <div class="rounded-3xl border border-base-200 bg-base-100/80 p-6">
              <div class="flex flex-col gap-2 border-b border-base-200 pb-4 md:flex-row md:items-end md:justify-between">
                <div>
                  <div class="block text-sm font-black text-base-content/80">
                    Step 2 · AI 对话配置
                  </div>
                  <p class="mt-2 text-xs leading-5 text-base-content/50">
                    这些设置会进入角色的聊天规则层，用来稳定回复风格、主动性和记忆方式。
                  </p>
                </div>
                <div class="text-xs leading-5 text-base-content/50">
                  配置面向创作者，不会直接暴露给普通用户。
                </div>
              </div>

              <div class="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <label class="form-control">
                  <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">回复风格</span>
                  <select v-model="replyStyle" class="select select-bordered mt-2 bg-base-100">
                    <option value="natural">自然</option>
                    <option value="warm">热情</option>
                    <option value="restrained">克制</option>
                    <option value="playful">俏皮</option>
                  </select>
                  <span class="mt-2 text-xs leading-5 text-base-content/50">{{ replyStyleDescription }}</span>
                </label>

                <label class="form-control">
                  <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">回复长度</span>
                  <select v-model="replyLength" class="select select-bordered mt-2 bg-base-100">
                    <option value="short">简短</option>
                    <option value="balanced">适中</option>
                    <option value="detailed">详细</option>
                  </select>
                </label>

                <label class="form-control">
                  <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">主动性</span>
                  <select v-model="initiativeLevel" class="select select-bordered mt-2 bg-base-100">
                    <option value="passive">被动回应</option>
                    <option value="balanced">适度追问</option>
                    <option value="proactive">积极引导</option>
                  </select>
                  <span class="mt-2 text-xs leading-5 text-base-content/50">{{ initiativeDescription }}</span>
                </label>

                <label class="form-control">
                  <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">记忆强度</span>
                  <select v-model="memoryMode" class="select select-bordered mt-2 bg-base-100">
                    <option value="off">关闭</option>
                    <option value="standard">标准</option>
                    <option value="enhanced">加强</option>
                  </select>
                </label>

                <label class="form-control">
                  <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">角色边界</span>
                  <select v-model="personaBoundary" class="select select-bordered mt-2 bg-base-100">
                    <option value="grounded">写实</option>
                    <option value="companion">陪伴</option>
                    <option value="dramatic">戏剧化</option>
                  </select>
                  <span class="mt-2 text-xs leading-5 text-base-content/50">{{ personaBoundaryDescription }}</span>
                </label>

                <div class="rounded-2xl border border-base-200 bg-base-200/40 px-4 py-3 text-xs leading-6 text-base-content/65">
                  <div class="font-bold text-base-content/80">当前策略摘要</div>
                  <div class="mt-1">风格：{{ replyStyle }}</div>
                  <div>长度：{{ replyLength }}</div>
                  <div>主动性：{{ initiativeLevel }}</div>
                  <div>记忆：{{ memoryMode }}</div>
                  <div>边界：{{ personaBoundary }}</div>
                </div>
              </div>

            </div>

            <div class="rounded-3xl border border-base-200 bg-base-100/80 p-6">
              <div class="flex flex-col gap-2 border-b border-base-200 pb-4 md:flex-row md:items-end md:justify-between">
                <div>
                  <label for="character-voice" class="block text-sm font-black text-base-content/80">
                    Step 3 · 语音配置
                  </label>
                  <p class="mt-2 text-xs leading-5 text-base-content/50">
                    在这里直接配置角色实际使用的音色。你可以选系统音色，也可以填写自己的阿里云 `voice_id`。
                  </p>
                </div>
                <div class="text-xs leading-5 text-base-content/50">
                  聊天播报和试听都会按这张卡片里的当前配置生效。
                </div>
              </div>

              <div class="mt-5 grid gap-4 md:grid-cols-[minmax(0,1fr)_220px]">
                <label class="form-control">
                  <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">系统音色</span>
                  <select
                    id="character-voice"
                    v-model="selectedVoiceId"
                    class="select select-bordered mt-2 h-12 w-full bg-base-100"
                  >
                    <option :value="null">使用默认播报</option>
                    <option v-for="voice in voices" :key="voice.id" :value="voice.id">
                      {{ voice.name }} · {{ voice.model_name }}
                    </option>
                  </select>
                </label>

                <div class="rounded-2xl border border-base-200 bg-base-200/40 px-4 py-3 text-xs leading-6 text-base-content/65">
                  <div v-if="selectedVoice">
                    <div class="font-bold text-base-content/75">
                      {{ selectedVoice.name }}
                    </div>
                    <div>{{ selectedVoice.model_name }} · {{ selectedVoice.source === 'custom' ? '自定义' : '系统' }}</div>
                    <div class="mt-1">
                      {{ selectedVoice.description || '已选中音色。' }}
                    </div>
                  </div>
                  <div v-else>
                    当前还没有选系统音色，可以直接在下面填写自定义音色。
                  </div>
                </div>
              </div>

              <div class="mt-5 rounded-2xl border border-dashed border-base-300 bg-base-100/70 p-5">
                <div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <div>
                    <div class="text-sm font-black text-base-content/80">自定义音色</div>
                    <p class="mt-2 text-xs leading-5 text-base-content/50">
                      如果你已经有阿里云声音复刻生成的 `voice_id`，直接填在这里就行。想做爱莉希雅，就把名称写成“爱莉希雅”，再填对应的 `voice_id`。
                    </p>
                  </div>
                  <div
                    v-if="selectedCustomVoice"
                    class="rounded-xl border border-base-200 bg-base-200/50 px-3 py-2 text-xs leading-5 text-base-content/65"
                  >
                    正在编辑：{{ selectedCustomVoice.name }}<br>
                    已被 {{ selectedCustomVoice.character_count }} 个角色引用
                  </div>
                </div>

                <div class="mt-4 grid gap-4 md:grid-cols-2">
                  <label class="form-control">
                    <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">音色名字</span>
                    <input
                      v-model="customVoiceName"
                      type="text"
                      class="input input-bordered mt-2 w-full bg-base-100"
                      placeholder="例如：爱莉希雅"
                    >
                  </label>

                  <label class="form-control">
                    <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">音色 ID</span>
                    <input
                      v-model="customVoiceCode"
                      type="text"
                      class="input input-bordered mt-2 w-full bg-base-100"
                      placeholder="填阿里云返回的 voice_id"
                    >
                  </label>

                  <label class="form-control">
                    <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">模型</span>
                    <input
                      v-model="customVoiceModelName"
                      type="text"
                      class="input input-bordered mt-2 w-full bg-base-100"
                      placeholder="cosyvoice-v3.5-plus"
                    >
                  </label>

                  <label class="form-control">
                    <span class="text-xs font-bold uppercase tracking-[0.16em] text-base-content/50">备注</span>
                    <input
                      v-model="customVoiceDescription"
                      type="text"
                      class="input input-bordered mt-2 w-full bg-base-100"
                      placeholder="例如：爱莉希雅风格自定义音色"
                    >
                  </label>
                </div>

                <div class="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    class="btn btn-outline btn-sm"
                    :disabled="pending || customVoicePending"
                    @click="saveCustomVoice"
                  >
                    {{ customVoicePending ? '保存中...' : (selectedCustomVoice ? '保存音色修改' : '保存为自定义音色') }}
                  </button>
                  <button
                    v-if="selectedCustomVoice"
                    type="button"
                    class="btn btn-ghost btn-sm text-error"
                    :disabled="pending || customVoicePending"
                    @click="removeCustomVoice"
                  >
                    删除这个音色
                  </button>
                  <button
                    type="button"
                    class="btn btn-ghost btn-sm"
                    :disabled="pending || customVoicePending"
                    @click="resetCustomVoiceDraft"
                  >
                    清空草稿
                  </button>
                </div>

                <div v-if="customVoiceMessage" class="alert alert-success mt-4 text-sm">
                  {{ customVoiceMessage }}
                </div>
                <div v-if="customVoiceError" class="alert alert-error mt-4 text-sm">
                  {{ customVoiceError }}
                </div>
              </div>

              <div v-if="props.showVoicePreview" class="mt-5 rounded-2xl border border-base-200 bg-base-100 p-5">
                <div class="text-sm font-black text-base-content/80">Step 4 · 语音试听</div>
                <p class="mt-2 text-xs leading-5 text-base-content/50">
                  先试听当前配置，再决定是否保存角色。这里会直接使用这张卡片里当前填写的音色信息。
                </p>

                <textarea
                  v-model="voicePreviewText"
                  class="textarea textarea-bordered mt-4 min-h-28 w-full bg-base-100"
                  maxlength="300"
                  placeholder="输入一段试听文案，例如：你好呀，我是爱莉希雅。"
                />

                <div class="mt-4 flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    class="btn btn-outline"
                    :disabled="pending"
                    @click="handlePreviewVoice"
                  >
                    {{ isPreviewingVoice ? '停止试听' : '试听音色' }}
                  </button>
                  <div class="text-xs text-base-content/55">
                    当前试听会直接反映这张卡片里的实际音色配置。
                  </div>
                </div>

                <div v-if="voicePreviewError" class="alert alert-error mt-4 text-sm">
                  {{ voicePreviewError }}
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <div class="space-y-8">
        <ImageCropField
          title="角色头像"
          helper="建议上传主体清晰的方图，头像会导出为轻量 WebP。"
          :model-value="photoPreview"
          :viewport-width="220"
          :aspect-ratio="1"
          :output-width="640"
          :output-format="'webp'"
          :output-quality="0.9"
          :max-file-size-m-b="8"
          @change="({ file, preview }) => {
            photoFile = file
            photoPreview = preview
            removePhoto = !file && !preview
          }"
        />

        <ImageCropField
          title="聊天背景"
          helper="推荐裁成竖向海报比例，系统会导出为更轻的 WebP，兼顾清晰度和加载速度。"
          :model-value="backgroundPreview"
          :viewport-width="220"
          :aspect-ratio="9 / 16"
          :output-width="1080"
          :output-format="'webp'"
          :output-quality="0.9"
          :max-file-size-m-b="12"
          @change="({ file, preview }) => {
            backgroundImageFile = file
            backgroundPreview = preview
            removeBackgroundImage = !file && !preview
          }"
        />

        <div class="rounded-3xl border border-base-200 bg-base-100 p-6 shadow-sm">
          <div class="text-sm leading-7 text-base-content/60">
            你可以先创建最小版本，后续再补背景、头像和详细设定。
          </div>
          <button type="submit" class="btn btn-primary mt-5 w-full" :disabled="pending">
            {{ pending ? '提交中...' : submitLabel }}
          </button>
        </div>
      </div>
    </div>
  </form>
</template>

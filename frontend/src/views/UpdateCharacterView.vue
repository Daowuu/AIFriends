<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '@/api/http'
import CharacterForm from '@/components/CharacterForm.vue'
import type { Character, CharacterFormPayload, VoiceOption } from '@/types/character'

const route = useRoute()
const router = useRouter()
const character = ref<Character | null>(null)
const voices = ref<VoiceOption[]>([])
const isLoading = ref(true)
const pending = ref(false)
const errorMessage = ref('')

const characterId = Number(route.params.id)

const loadVoices = async () => {
  const response = await api.get<{ voices: VoiceOption[] }>('/create/character/voice/list/')
  voices.value = response.data.voices
}

const loadCharacter = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await api.get<{ character: Character }>(`/create/character/${characterId}/`)
    character.value = response.data.character
  } catch (error: unknown) {
    errorMessage.value = '角色信息加载失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    isLoading.value = false
  }
}

const handleSubmit = async (payload: CharacterFormPayload) => {
  pending.value = true
  errorMessage.value = ''

  try {
    const formData = new FormData()
    formData.append('name', payload.name)
    formData.append('profile', payload.profile)
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

    const response = await api.post<{ character: Character }>(
      `/create/character/${characterId}/update/`,
      formData,
    )
    character.value = response.data.character
  } catch (error: unknown) {
    errorMessage.value = '保存角色失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as {
        response?: { data?: { detail?: string } }
      }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    pending.value = false
  }
}

const removeCharacter = async () => {
  await api.post(`/create/character/${characterId}/remove/`)
  await router.push('/workspace')
}

onMounted(() => {
  void loadVoices()
  void loadCharacter()
})
</script>

<template>
  <section class="mx-auto max-w-6xl p-6">
    <div class="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-3xl font-black">编辑角色</h1>
        <p class="mt-2 text-sm text-base-content/60">
          角色修改会即时覆盖上一次保存的版本。
        </p>
      </div>
      <button type="button" class="btn btn-ghost text-error" @click="removeCharacter">
        删除角色
      </button>
    </div>

    <div v-if="errorMessage" class="alert alert-error mb-6">{{ errorMessage }}</div>

    <div
      v-if="isLoading"
      class="grid min-h-56 place-items-center rounded-[32px] border border-base-200 bg-base-100 text-base-content/55 shadow-sm"
    >
      正在加载角色...
    </div>

    <CharacterForm
      v-else
      mode="update"
      :initial-character="character"
      :voices="voices"
      :pending="pending"
      @submit="handleSubmit"
      @voices-changed="() => { void loadVoices(); void loadCharacter() }"
    />
  </section>
</template>

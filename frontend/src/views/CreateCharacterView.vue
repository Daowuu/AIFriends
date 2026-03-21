<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import api from '@/api/http'
import CharacterForm from '@/components/CharacterForm.vue'
import type { CharacterFormPayload, VoiceOption } from '@/types/character'

const router = useRouter()
const pending = ref(false)
const errorMessage = ref('')
const voices = ref<VoiceOption[]>([])

const loadVoices = async () => {
  const response = await api.get<{ voices: VoiceOption[] }>('/create/character/voice/list/')
  voices.value = response.data.voices
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
    if (payload.photoFile) formData.append('photo', payload.photoFile)
    if (payload.backgroundImageFile) formData.append('background_image', payload.backgroundImageFile)

    const response = await api.post<{ character: { id: number } }>('/create/character/create/', formData)
    await router.push(`/characters/${response.data.character.id}/edit`)
  } catch (error: unknown) {
    errorMessage.value = '创建角色失败。'
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

onMounted(() => {
  void loadVoices()
})
</script>

<template>
  <section class="mx-auto max-w-6xl p-6">
    <div class="mb-8">
      <h1 class="text-3xl font-black">创建角色</h1>
      <p class="mt-2 text-sm text-base-content/60">
        先把角色基础设定建立起来，后面再继续细化聊天风格和人物关系。
      </p>
    </div>

    <div v-if="errorMessage" class="alert alert-error mb-6">{{ errorMessage }}</div>

    <CharacterForm mode="create" :voices="voices" :pending="pending" @submit="handleSubmit" @voices-changed="loadVoices" />
  </section>
</template>

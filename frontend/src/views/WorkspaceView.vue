<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import api from '@/api/http'
import AppIcon from '@/components/AppIcon.vue'
import CharacterCard from '@/components/character/CharacterCard.vue'
import type { Character } from '@/types/character'
import { useCharacterChatNavigation } from '@/utils/useCharacterChatNavigation'

const characters = ref<Character[]>([])
const isLoading = ref(true)
const errorMessage = ref('')
const { openCharacterChat } = useCharacterChatNavigation()

const loadCharacters = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await api.get<{ characters: Character[] }>('/create/character/list/')
    characters.value = response.data.characters
  } catch (error: unknown) {
    errorMessage.value = '角色列表加载失败。'
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

const removeCharacter = async (characterId: number) => {
  await api.post(`/create/character/${characterId}/remove/`)
  characters.value = characters.value.filter((character) => character.id !== characterId)
}

onMounted(() => {
  void loadCharacters()
})
</script>

<template>
  <section class="mx-auto max-w-6xl p-6">
    <div class="mb-6 flex flex-col gap-4 rounded-[32px] border border-base-200 bg-base-100 p-6 shadow-sm md:flex-row md:items-center md:justify-between">
      <div>
        <h1 class="text-3xl font-black">创作工作区</h1>
        <p class="mt-2 text-sm text-base-content/60">
          管理你的角色设定，后续聊天、投稿和对话页都可以复用这里的角色。
        </p>
      </div>
      <RouterLink to="/characters/create" class="btn btn-primary">
        <AppIcon name="create" icon-class="h-4 w-4" />
        新建角色
      </RouterLink>
    </div>

    <div v-if="errorMessage" class="alert alert-error mb-6">{{ errorMessage }}</div>

    <div
      v-if="isLoading"
      class="grid min-h-56 place-items-center rounded-[32px] border border-base-200 bg-base-100 text-base-content/50 shadow-sm"
    >
      正在加载角色列表...
    </div>

    <div
      v-else-if="characters.length === 0"
      class="grid min-h-72 place-items-center rounded-[32px] border border-dashed border-base-300 bg-base-100 p-6 text-center shadow-sm"
    >
      <div>
        <div class="mx-auto grid h-16 w-16 place-items-center rounded-3xl bg-base-200">
          <AppIcon name="create" icon-class="h-7 w-7" />
        </div>
        <h2 class="mt-4 text-xl font-black">还没有角色</h2>
        <p class="mt-2 text-sm text-base-content/60">
          先创建一个角色，后面就能接聊天背景、头像和设定文案。
        </p>
        <RouterLink to="/characters/create" class="btn btn-primary mt-5">
          立即创建
        </RouterLink>
      </div>
    </div>

    <div v-else class="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-7 justify-items-stretch">
      <CharacterCard
        v-for="character in characters"
        :key="character.id"
        :character="character"
        mode="space-owner"
        @edit="$router.push(`/characters/${character.id}/edit`)"
        @chat="openCharacterChat"
        @remove="removeCharacter($event.id)"
        @open="$router.push(`/characters/${character.id}/edit`)"
      />
    </div>
  </section>
</template>

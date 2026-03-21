<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import api from '@/api/http'
import CharacterCard from '@/components/character/CharacterCard.vue'
import { useUserStore } from '@/stores/user'
import type { Character, CharacterAuthor } from '@/types/character'
import { useCharacterChatNavigation } from '@/utils/useCharacterChatNavigation'

import UserInfoField from './space/components/UserInfoField.vue'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const { openCharacterChat } = useCharacterChatNavigation()

const author = ref<CharacterAuthor | null>(null)
const characters = ref<Character[]>([])
const isInitialLoading = ref(true)
const isLoadingMore = ref(false)
const errorMessage = ref('')
const hasMore = ref(true)
const nextOffset = ref(0)
const sentinelRef = ref<HTMLDivElement | null>(null)

let observer: IntersectionObserver | null = null

const userId = computed(() => Number(route.params.id))
const isOwnSpace = computed(() => user.userInfo?.id === author.value?.id)

const replaceCharacter = (characterId: number, updater: (character: Character) => Character) => {
  characters.value = characters.value.map((character) => (
    character.id === characterId ? updater(character) : character
  ))
}

const loadMore = async ({ reset = false } = {}) => {
  if (isLoadingMore.value) return
  if (!hasMore.value && !reset) return

  if (reset) {
    characters.value = []
    nextOffset.value = 0
    hasMore.value = true
    isInitialLoading.value = true
  }

  isLoadingMore.value = true
  errorMessage.value = ''

  try {
    const response = await api.get<{
      author: CharacterAuthor
      characters: Character[]
      has_more: boolean
      next_offset: number
    }>(`/user/space/${userId.value}/`, {
      params: {
        offset: nextOffset.value,
        limit: 12,
      },
    })

    author.value = response.data.author
    characters.value = reset
      ? response.data.characters
      : [...characters.value, ...response.data.characters]
    hasMore.value = response.data.has_more
    nextOffset.value = response.data.next_offset
  } catch (error: unknown) {
    errorMessage.value = '个人主页加载失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    isLoadingMore.value = false
    isInitialLoading.value = false
  }
}

const editCharacter = async (character: Character) => {
  await router.push(`/characters/${character.id}/edit`)
}

const deleteCharacter = async (character: Character) => {
  await api.post(`/create/character/${character.id}/remove/`)
  characters.value = characters.value.filter((item) => item.id !== character.id)
}

const openCharacter = async (character: Character) => {
  if (isOwnSpace.value) {
    await editCharacter(character)
    return
  }

  const nextCharacter = await openCharacterChat(character)
  if (!nextCharacter) return
  replaceCharacter(character.id, () => nextCharacter)
}

const openCharacterChatFromOwnerSpace = async (character: Character) => {
  const nextCharacter = await openCharacterChat(character)
  if (!nextCharacter) return
  replaceCharacter(character.id, () => nextCharacter)
}

const setupObserver = () => {
  if (!sentinelRef.value) return

  observer?.disconnect()
  observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        void loadMore()
      }
    })
  }, { root: null, rootMargin: '160px', threshold: 0 })
  observer.observe(sentinelRef.value)
}

watch(() => route.params.id, () => {
  author.value = null
  void loadMore({ reset: true }).then(async () => {
    await nextTick()
    setupObserver()
  })
})

onMounted(async () => {
  await loadMore({ reset: true })
  await nextTick()
  setupObserver()
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <section class="mx-auto max-w-[1280px] p-6">
    <div v-if="author" class="mb-8">
      <UserInfoField :author="author" />
    </div>

    <div v-if="errorMessage" class="alert alert-error mb-6">{{ errorMessage }}</div>

    <div
      v-if="isInitialLoading"
      class="grid min-h-64 place-items-center rounded-[32px] border border-base-200 bg-base-100 text-base-content/55 shadow-sm"
    >
      正在加载主页内容...
    </div>

    <template v-else>
      <div class="mb-5 flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-black">
            {{ isOwnSpace ? '我的角色' : 'TA 的角色' }}
          </h2>
          <p class="mt-1 text-sm text-base-content/55">
            共展示 {{ characters.length }} 个角色，滚动到底部会继续加载。
          </p>
        </div>
      </div>

      <div
        v-if="characters.length === 0"
        class="grid min-h-56 place-items-center rounded-[32px] border border-dashed border-base-300 bg-base-100 text-base-content/50 shadow-sm"
      >
        这个主页暂时还没有角色。
      </div>

      <div
        v-else
        class="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-7 justify-items-stretch"
      >
        <CharacterCard
          v-for="character in characters"
          :key="character.id"
          :character="character"
          :mode="isOwnSpace ? 'space-owner' : 'feed'"
          @open="openCharacter"
          @chat="openCharacterChatFromOwnerSpace"
          @edit="editCharacter"
          @remove="deleteCharacter"
        />
      </div>

      <div ref="sentinelRef" class="h-8" />
      <div v-if="isLoadingMore" class="pb-8 text-center text-sm text-base-content/50">
        正在加载更多角色...
      </div>
    </template>
  </section>
</template>

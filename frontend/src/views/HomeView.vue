<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import api from '@/api/http'
import AppIcon from '@/components/AppIcon.vue'
import CharacterCard from '@/components/character/CharacterCard.vue'
import type { Character } from '@/types/character'
import { useCharacterChatNavigation } from '@/utils/useCharacterChatNavigation'

const route = useRoute()
const { openCharacterChat } = useCharacterChatNavigation()

const characters = ref<Character[]>([])
const isInitialLoading = ref(true)
const isLoadingMore = ref(false)
const errorMessage = ref('')
const hasMore = ref(true)
const nextOffset = ref(0)
const sentinelRef = ref<HTMLDivElement | null>(null)

let observer: IntersectionObserver | null = null

const queryText = computed(() => String(route.query.q || '').trim())

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
      characters: Character[]
      has_more: boolean
      next_offset: number
    }>('/homepage/index/', {
      params: {
        q: queryText.value,
        offset: nextOffset.value,
        limit: 12,
      },
    })

    characters.value = reset
      ? response.data.characters
      : [...characters.value, ...response.data.characters]
    hasMore.value = response.data.has_more
    nextOffset.value = response.data.next_offset
  } catch (error: unknown) {
    errorMessage.value = '首页角色流加载失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    isLoadingMore.value = false
    isInitialLoading.value = false
  }
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

const openCharacter = async (character: Character) => {
  const nextCharacter = await openCharacterChat(character)
  if (!nextCharacter) return
  replaceCharacter(character.id, () => nextCharacter)
}

watch(() => route.query.q, () => {
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
  <section class="mx-auto w-full max-w-[104rem] px-4 py-6 sm:px-6 xl:px-8">
    <div class="mb-8 grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(18rem,0.82fr)]">
      <div class="overflow-hidden rounded-[34px] border border-base-200 bg-base-100 shadow-sm">
        <div class="grid gap-6 p-7 xl:grid-cols-[minmax(0,1.35fr)_minmax(14rem,0.75fr)] xl:items-center">
          <div>
            <div class="inline-flex items-center rounded-full bg-base-200 px-3 py-1 text-xs font-black tracking-[0.22em] text-base-content/60">
              ROLE LIBRARY
            </div>
            <h1 class="mt-4 text-4xl font-black tracking-tight text-base-content">
              发现角色，进入聊天页，直接开聊。
            </h1>
            <p class="mt-3 max-w-2xl text-sm leading-7 text-base-content/60">
              首页已经接入搜索和流式加载。你可以按角色名、介绍、Prompt 关键词搜索，点进角色后会直接进入沉浸式聊天页。
            </p>
            <div v-if="queryText" class="mt-5 inline-flex rounded-full bg-amber-100 px-4 py-2 text-sm font-bold text-amber-800">
              当前搜索：{{ queryText }}
            </div>
            <div class="mt-6 flex flex-wrap gap-3">
              <RouterLink
                to="/werewolf"
                class="inline-flex items-center gap-2 rounded-full border border-[#d4c7ae] bg-white/82 px-5 py-3 text-sm font-bold text-[#22302b] transition hover:bg-[#fff7e7]"
              >
                <AppIcon name="game" icon-class="h-4 w-4" />
                去狼人杀实验场
              </RouterLink>
            </div>
          </div>

          <div class="grid gap-3">
            <div class="rounded-[28px] border border-base-200 bg-base-50 p-5">
              <div class="text-sm text-base-content/45">当前角色数</div>
              <div class="mt-2 text-3xl font-black">{{ characters.length }}</div>
            </div>
            <div class="rounded-[28px] border border-base-200 bg-base-50 p-5">
              <div class="text-sm text-base-content/45">聊天入口</div>
              <div class="mt-2 text-lg font-black">独立页面</div>
            </div>
          </div>
        </div>
      </div>

      <aside class="rounded-[34px] border border-base-200 bg-base-100 p-6 shadow-sm">
        <div class="flex items-center gap-3">
          <AppIcon name="search" icon-class="h-5 w-5" />
          <div class="text-base font-black">浏览提示</div>
        </div>
        <ul class="mt-5 space-y-3 text-sm leading-7 text-base-content/65">
          <li class="rounded-2xl border border-base-200 px-4 py-3">点击角色卡片会直接进入聊天页。</li>
          <li class="rounded-2xl border border-base-200 px-4 py-3">所有角色都来自本地单实例工作台，首页只负责筛选和进入聊天。</li>
          <li class="rounded-2xl border border-base-200 px-4 py-3">文字聊天、语音输入和语音播报共用同一套角色逻辑。</li>
          <li class="rounded-2xl border border-base-200 px-4 py-3">如果你想看多角色同局流程，可以从导航或这里进入狼人杀模式。</li>
        </ul>
      </aside>
    </div>

    <div v-if="errorMessage" class="alert alert-error mb-6">{{ errorMessage }}</div>

    <div
      v-if="isInitialLoading"
      class="grid min-h-72 place-items-center rounded-[32px] border border-base-200 bg-base-100 text-base-content/55 shadow-sm"
    >
      正在加载角色列表...
    </div>

    <template v-else>
      <div
        v-if="characters.length === 0"
        class="grid min-h-64 place-items-center rounded-[32px] border border-dashed border-base-300 bg-base-100 text-base-content/50 shadow-sm"
      >
        没有搜到符合条件的角色。
      </div>

      <div
        v-else
        class="flex flex-wrap gap-6 xl:gap-7"
      >
        <div
          v-for="character in characters"
          :key="character.id"
          class="w-full sm:w-[18.5rem] xl:w-[19rem] 2xl:w-[19.5rem]"
        >
          <CharacterCard
            :character="character"
            @open="openCharacter"
          />
        </div>
      </div>

      <div ref="sentinelRef" class="h-8" />
      <div v-if="isLoadingMore" class="pb-8 text-center text-sm text-base-content/50">
        正在加载更多角色...
      </div>
    </template>
  </section>
</template>

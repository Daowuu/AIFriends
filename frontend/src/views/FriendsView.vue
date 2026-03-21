<script setup lang="ts">
import { onMounted, ref } from 'vue'

import api from '@/api/http'
import AppIcon from '@/components/AppIcon.vue'
import CharacterCard from '@/components/character/CharacterCard.vue'
import type { Character } from '@/types/character'
import type { Friend } from '@/types/friend'
import { useCharacterChatNavigation } from '@/utils/useCharacterChatNavigation'

const { openCharacterChat } = useCharacterChatNavigation()

const friends = ref<Friend[]>([])
const isLoading = ref(true)
const errorMessage = ref('')
const pendingRemoveId = ref<number | null>(null)

const loadFriends = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await api.get<{ friends: Friend[] }>('/friend/list/')
    friends.value = response.data.friends
  } catch (error: unknown) {
    errorMessage.value = '好友列表加载失败。'
    if (typeof error === 'object' && error && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response
      errorMessage.value = response?.data?.detail || errorMessage.value
    }
  } finally {
    isLoading.value = false
  }
}

const removeFriend = async (character: Character) => {
  if (!character.friend_id) return
  pendingRemoveId.value = character.friend_id

  try {
    await api.post('/friend/remove/', {
      friend_id: character.friend_id,
    })
    friends.value = friends.value.filter((friend) => friend.id !== character.friend_id)
  } finally {
    pendingRemoveId.value = null
  }
}

const openCharacter = async (character: Character) => {
  await openCharacterChat(character)
}

onMounted(() => {
  void loadFriends()
})
</script>

<template>
  <section class="mx-auto max-w-[1280px] p-6">
    <div class="mb-6 flex flex-col gap-4 rounded-[34px] border border-base-200 bg-base-100 p-6 shadow-sm md:flex-row md:items-center md:justify-between">
      <div class="flex items-center gap-4">
        <div class="grid h-14 w-14 place-items-center rounded-3xl bg-base-200">
          <AppIcon name="friend" icon-class="h-7 w-7" />
        </div>
        <div>
          <h1 class="text-3xl font-black">好友页面</h1>
          <p class="mt-2 text-sm text-base-content/60">
            这里展示你已经添加过的角色好友，点击卡片会直接进入聊天页。
          </p>
        </div>
      </div>
      <div class="rounded-2xl bg-base-50 px-4 py-3 text-sm font-bold text-base-content/65">
        当前好友数：{{ friends.length }}
      </div>
    </div>

    <div v-if="errorMessage" class="alert alert-error mb-6">{{ errorMessage }}</div>

    <div
      v-if="isLoading"
      class="grid min-h-64 place-items-center rounded-[32px] border border-base-200 bg-base-100 text-base-content/55 shadow-sm"
    >
      正在加载好友列表...
    </div>

    <div
      v-else-if="friends.length === 0"
      class="grid min-h-64 place-items-center rounded-[32px] border border-dashed border-base-300 bg-base-100 text-center text-base-content/55 shadow-sm"
    >
      <div>
        <h2 class="text-xl font-black">还没有好友</h2>
        <p class="mt-2 text-sm">去首页或别人的主页里挑一个角色开始聊天吧。</p>
      </div>
    </div>

    <div
      v-else
      class="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-7 justify-items-stretch"
    >
      <CharacterCard
        v-for="friend in friends"
        :key="friend.id"
        :character="friend.character"
        mode="friend"
        @open="openCharacter"
        @remove="removeFriend"
      />
    </div>
  </section>
</template>
